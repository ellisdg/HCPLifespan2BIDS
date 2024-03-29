import argparse
import os
import glob
import warnings
import json

__version__ = "0.1.0"

from utils import fix_epi_runs, generate_intended_for, move_to_bids, spin_echo_intended_for


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, required=True,
                        help="path to output BIDS directory.")
    parser.add_argument("--dry_run", action="store_true", help="do not write files, just print what would be done.")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing files.")
    parser.add_argument("--method", type=str, default="hardlink", choices=["hardlink", "symlink", "copy", "move"],
                        help="method to use for linking files.")
    parser.add_argument("--use_bids_uris", action="store_true",
                        help="use BIDS URIs for setting the IntendedFor field for single bad reference and spin echo "
                             "images. This is now required by BIDS, but I am not making it the default because fMRIprep"
                             " does not support it yet. "
                             "(https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html#using-intendedfor-metadata)")

    return parser


def parse_args():
    parser = create_parser()
    parser.add_argument("--nda_dir", type=str, required=True,
                        help="path to nda directory containing the unprocessed imagingcollection for the"
                             "HCP Aging or HCP Development datasets.")
    parser.add_argument("--name", type=str, default="auto",
                        help="name of the dataset. (default: 'auto'). 'auto' will try to determine if the dataset is "
                             "the HCP Aging or HCP Development dataset based on the contents of the nda_dir.")
    return parser.parse_args()


def write_bids_dataset_metadata_files(bids_dir, name):
    # write dataset_description.json
    dataset_description = {"Name": name, "BIDSVersion": "1.8.0", "DatasetType": "raw",
                           "GeneratedBy": [{"Name": "HCPLifespanBIDS", "Version": __version__,
                                           "CodeURL": "https://github.com/ellisdg/HCPLifespan2BIDS"}]}
    with open(os.path.join(bids_dir, "dataset_description.json"), "w") as f:
        json.dump(dataset_description, f, indent=4, sort_keys=False)

    # write README
    with open(os.path.join(bids_dir, "README"), "w") as f:
        f.write("This is a BIDS dataset generated from the HCP Lifespan datasets using HCPLifespan2BIDS.\n")

    # write bidsignore
    with open(os.path.join(bids_dir, ".bidsignore"), "w") as f:
        f.write("*.mp4\n")
        # TODO: convert physio files to tsv and make sure the correct columns are present
        f.write("*_physio.csv\n")
        # TODO: fix metadata for ASL files so that it conforms to BIDS standard
        f.write("perf/\n")


def get_dataset_name(name, subject_id):
    if name == "auto":
        if "HCD" in subject_id:
            name = "HCPDevelopment"
        elif "HCA" in subject_id:
            name = "HCPAging"
        else:
            warnings.warn("Could not detect name of HCP project from subject_id: {}.\n"
                          "Setting dataset name to 'HCPUnknown'.".format(subject_id))
            name = "HCPUnknown"
    return name


def parse_phase_encoding_direction(image_file, dirs=("AP", "PA")):
    for dir in dirs:
        if f"_{dir}" in os.path.basename(image_file):
            return dir
    return None


def set_phase_encoding_direction(kwargs, image_file, dirs=("AP", "PA")):
    pe_dir = parse_phase_encoding_direction(image_file, dirs=dirs)
    if pe_dir is not None:
        kwargs["dir"] = pe_dir


def find_gradient_warped_file(image_file):
    gradunwarp_file = image_file.replace("unprocessed/3T", "gradunwarp")
    if not os.path.exists(gradunwarp_file):
        raise ValueError(f"Gradient unwarped file not found: {gradunwarp_file}")
    return gradunwarp_file


def run(wildcard, use_bids_uris=False, pe_dirs=("AP", "PA"), output_dir=".", method="hardlink", overwrite=False,
        dry_run=False, name="auto", grad_unwarp=False, skip_bias=True, t1w_use_derived=False, t2w_use_derived=False,
        skip=(), use_precompiled_sidecars=False):
    print("Searching for subjects with wildcard: {}".format(wildcard))
    subject_folders = sorted(glob.glob(wildcard))
    print("Found {} subjects.".format(len(subject_folders)))
    for subject_folder in subject_folders:
        print("Processing subject: {}".format(subject_folder))
        subject_id = os.path.basename(subject_folder).split("_")[0]

        image_files = glob.glob(os.path.join(subject_folder, "unprocessed/**/*.nii.gz"), recursive=True)
        print("Found {} image files.".format(len(image_files)))
        for image_file in image_files:

            if os.path.dirname(image_file).endswith("OTHER_FILES"):
                continue

            if skip_bias and "BIAS" in image_file:
                continue

            if any([skip_str in image_file for skip_str in skip]):
                continue

            print("Processing image file: {}".format(image_file))

            kwargs = dict()
            intended_for = None

            set_phase_encoding_direction(kwargs, image_file, dirs=pe_dirs)

            if "SpinEchoFieldMap" in image_file:
                bids_modality = "epi"
                folder = "fmap"
                basename = os.path.basename(os.path.dirname(image_file))
                run = basename.lower()
                if "_" in run:
                    run = "".join(run.split("_")[1:]).lower()
                # match = re.search(r"SpinEchoFieldMap(\d+)", image_file)
                # if match:
                #     run = run + match.group(1)
                kwargs["run"] = run
                intended_for = spin_echo_intended_for(subject_id, use_bids_uris, basename, image_file)

            elif "T1w" in image_file:
                folder = "anat"
                bids_modality = "T1w"
                if t1w_use_derived:
                    image_file = os.path.join(image_file.split("unprocessed")[0], "T1w", "T1w_acpc_dc.nii.gz")
                    if not os.path.exists(image_file):
                        raise ValueError(f"Derived T1w file not found: {image_file}")
            elif "T2w" in image_file:
                folder = "anat"
                bids_modality = "T2w"
                if t2w_use_derived:
                    image_file = os.path.join(image_file.split("unprocessed")[0], "T1w", "T2w_acpc_dc.nii.gz")
                    if not os.path.exists(image_file):
                        raise ValueError(f"Derived T2w file not found: {image_file}")
            elif "fMRI" in image_file:
                if grad_unwarp:
                    image_file = find_gradient_warped_file(image_file)
                folder = "func"
                bids_modality = "bold"
                task = os.path.basename(os.path.dirname(image_file))
                if "_" in task:
                    task = task.split("_")[1].lower()
                if "rest" in task:
                    run = task.split("rest")[1]
                    task = "rest"
                    kwargs["run"] = run
                kwargs["task"] = task
            elif "Diffusion" in image_file:
                folder = "dwi"
                bids_modality = "dwi"
                # dir 98 scans are acquired before dir99 scans
                if "dir98" in image_file:
                    kwargs["run"] = "1"
                elif "dir99" in image_file:
                    kwargs["run"] = "2"
            elif "PCASL" in image_file:
                bids_modality = "asl"
                folder = "perf"
            else:
                folder = None
                bids_modality = None
                print("Unknown modality: {}".format(image_file))

            if "SBRef" in image_file:
                intended_for = generate_intended_for(subject_id=subject_id, modality=bids_modality, folder=folder,
                                                     bids_uris=use_bids_uris, **kwargs)
                # overwrite the modality to be sbref
                bids_modality = "sbref"

            move_to_bids(image_file=image_file, bids_dir=output_dir, subject_id=subject_id, folder=folder,
                         modality=bids_modality, method=method, overwrite=overwrite, dryrun=dry_run,
                         intended_for=intended_for, use_precompiled_sidecars=use_precompiled_sidecars, **kwargs)

    first_subject_id = os.path.basename(subject_folders[0]).split("_")[0]
    write_bids_dataset_metadata_files(output_dir, name=get_dataset_name(name, first_subject_id))
    if not dry_run:
        fix_epi_runs(output_dir, pe_dirs=pe_dirs)


def main():
    args = parse_args()
    wildcard = os.path.join(args.nda_dir, "imagingcollection01/HC*")
    run(wildcard,
        use_bids_uris=args.use_bids_uris,
        pe_dirs=("AP", "PA"),
        output_dir=args.output_dir,
        method=args.method,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        name=args.name)


if __name__ == "__main__":
    main()
