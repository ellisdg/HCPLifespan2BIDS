import argparse
import os
import glob
import shutil
import warnings
import json
import re

__version__ = "0.1.0"


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


def generate_output_filename(subject_id, modality, folder, extension=".nii.gz", **kwargs):
    args = ["sub-{}".format(subject_id)]
    # Makes sure the arguments are added in the correct order
    # fix run if it has 1a, 1b, 2a, 2b
    if "run" in kwargs:
        if kwargs["run"] == "1a":
            kwargs["run"] = 1
        elif kwargs["run"] == "1b":
            kwargs["run"] = 2
        elif kwargs["run"] == "2a":
            kwargs["run"] = 3
        elif kwargs["run"] == "2b":
            kwargs["run"] = 4

    for key in ("ses", "task", "acq", "ce", "rec", "dir", "run", "recording", "echo", "part"):
        if key in kwargs:
            value = kwargs[key]
            args.append("{}-{}".format(key, value))
    args.append(modality)
    return os.path.join(folder, "_".join(args) + extension)


def generate_full_output_filename(bids_dir, subject_id, modality, folder, extension=".nii.gz", **kwargs):
    return os.path.join(bids_dir, "sub-{}".format(subject_id),
                        generate_output_filename(subject_id, modality, folder, extension=extension, **kwargs))


def generate_intended_for(subject_id, modality, folder, bids_uris=False, **kwargs):
    if bids_uris:
        return "bids::sub-{}/{}".format(subject_id, generate_output_filename(subject_id, modality, folder, **kwargs))
    else:
        return generate_output_filename(subject_id, modality, folder, **kwargs)


def add_intended_for_to_json(json_file, intended_for):
    if os.path.exists(json_file):
        print("Adding IntendedFor to {}".format(json_file))
        with open(json_file, "r") as f:
            json_dict = json.load(f)
    else:
        print("Adding IntendedFor to new JSON file: {}".format(json_file))
        json_dict = dict()
    json_dict["IntendedFor"] = intended_for
    with open(json_file, "w") as f:
        json.dump(json_dict, f, indent=4, sort_keys=True)


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


def move_to_bids(image_file, bids_dir, subject_id, modality, folder, method="hardlink", overwrite=False, dryrun=False,
                 intended_for=None, exists_ok=True, **kwargs):
    output_file = generate_full_output_filename(bids_dir, subject_id, modality, folder, **kwargs)
    in_files = [image_file]
    out_files = [output_file]
    json_sidecar = image_file.replace(".nii.gz", ".json")
    output_json_sidecar = output_file.replace(".nii.gz", ".json")
    if os.path.exists(json_sidecar):
        in_files.append(json_sidecar)
        out_files.append(output_json_sidecar)
    else:
        warnings.warn("No JSON sidecar found for {}".format(image_file))

    if modality == "dwi":
        # check for bval and bvec files
        bval_file = image_file.replace(".nii.gz", ".bval")
        bvec_file = image_file.replace(".nii.gz", ".bvec")
        if os.path.exists(bval_file):
            in_files.append(bval_file)
            out_files.append(output_file.replace(".nii.gz", ".bval"))
        else:
            warnings.warn("No bval file found for {}".format(image_file))
        if os.path.exists(bvec_file):
            in_files.append(bvec_file)
            out_files.append(output_file.replace(".nii.gz", ".bvec"))
        else:
            warnings.warn("No bvec file found for {}".format(image_file))
    elif modality == "bold":
        # add physio, eye tracking, and events files
        # check for physio files
        physio_files = glob.glob(os.path.join(os.path.dirname(image_file), "LINKED_DATA", "PHYSIO", "*.csv"))
        if len(physio_files) == 1:
            in_files.append(physio_files[0])
            out_files.append(output_file.replace("_bold.nii.gz", "_physio.csv"))
        elif len(physio_files) > 1:
            warnings.warn("Found multiple physio files for {}. Skipping.".format(image_file))

        # check for eye tracking file
        eye_tracking_files = glob.glob(os.path.join(os.path.dirname(image_file), "LINKED_DATA", "PSYCHOPY", "*.mp4"))
        if len(eye_tracking_files) == 1:
            in_files.append(eye_tracking_files[0])
            out_files.append(generate_full_output_filename(bids_dir, subject_id, modality="physio", folder=folder,
                                                           recording="eyetracking", extension=".mp4", **kwargs))
        elif len(eye_tracking_files) > 1:
            warnings.warn("Found multiple eye tracking files for {}. Skipping.".format(image_file))

        # check for events files
        events_files = glob.glob(os.path.join(os.path.dirname(image_file), "LINKED_DATA", "PSYCHOPY", "EVs", "*txt"))
        # combine all events files into one tsv file
        tsv_output_file = generate_full_output_filename(bids_dir, subject_id, modality="events", folder=folder,
                                                        extension=".tsv", **kwargs)
        tsv_header = ["onset", "duration", "value", "trial_type"]
        if len(events_files) > 0 and not dryrun and (overwrite or not os.path.exists(tsv_output_file)):
            print("Combining events files into {}".format(tsv_output_file))
            with open(tsv_output_file, "w") as f:
                f.write("\t".join(tsv_header) + "\n")
                rows = list()
                for events_file in events_files:
                    trial_type = os.path.basename(events_file).replace(".txt", "")
                    with open(events_file, "r") as f2:
                        for line in f2.readlines():
                            rows.append(line.strip().split(" ") + [trial_type])
                # sort the rows by onset
                rows.sort(key=lambda x: float(x[0]))
                for row in rows:
                    f.write("\t".join(row) + "\n")

    if os.path.exists(output_file):
        if exists_ok and not overwrite:
            warnings.warn("File already exists: {}".format(output_file))
            return
        elif not overwrite:
            raise FileExistsError("File already exists: {}".format(output_file))
        elif overwrite:
            print("Overwriting file: {}".format(output_file))
            if not dryrun:
                for file in out_files:
                    if os.path.exists(file):
                        os.remove(file)

    print_text = "\n".join(["{} --> {}".format(in_file, out_file) for in_file, out_file in zip(in_files, out_files)])

    if not dryrun:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if method == "hardlink":
        print("Creating hardlink: {}".format(print_text))
        if not dryrun:
            for in_file, out_file in zip(in_files, out_files):
                os.link(in_file, out_file)
    elif method == "symlink":
        print("Creating symlink: {}".format(print_text))
        if not dryrun:
            for in_file, out_file in zip(in_files, out_files):
                os.symlink(in_file, out_file)
    elif method == "copy":
        print("Copying file: {}".format(print_text))
        if not dryrun:
            for in_file, out_file in zip(in_files, out_files):
                shutil.copy(in_file, out_file)
    elif method == "move":
        print("Moving file: {}".format(print_text))
        if not dryrun:
            for in_file, out_file in zip(in_files, out_files):
                shutil.move(in_file, out_file)
    else:
        raise ValueError("Unknown method: {}".format(method))

    if intended_for is not None and not dryrun:
        add_intended_for_to_json(output_json_sidecar, intended_for)

    if "task-" in os.path.basename(output_file) and not dryrun:
        # add task name to json sidecar
        # get task name from filename using regular expression
        task_name = re.search("task-([a-zA-Z0-9]+)_", os.path.basename(output_file)).group(1)
        add_task_name_to_json(output_json_sidecar, task_name)


def add_task_name_to_json(json_file, task_name):
    print("Adding task name {} to {}".format(task_name, json_file))
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            data = json.load(f)
    else:
        data = dict()
    data["TaskName"] = task_name
    with open(json_file, "w") as f:
        json.dump(data, f, indent=4)


def get_acquisition_time(image_file):
    json_sidecar = image_file.replace(".nii.gz", ".json")
    if not os.path.exists(json_sidecar):
        raise ValueError("No json sidecar found for {}".format(image_file))
    with open(json_sidecar, "r") as f:
        data = json.load(f)
    return data["AcquisitionTime"]


def fix_epi_runs(bids_dir):
    # The epi runs must be renamed to match the BIDS standard
    # this script will assign each epi run a number according to the acquisition time of the volume
    # the first run will be 1, the second run will be 2, etc.
    fmap_folders = glob.glob(os.path.join(bids_dir, "sub-*", "fmap"))
    for fmap_folder in fmap_folders:
        for dir in ("AP", "PA"):  # this is a bit of a hack to just get the epi runs for the same direction
            epi_runs = glob.glob(os.path.join(fmap_folder, "*dir-{}*epi.nii.gz".format(dir)))
            new_runs = list()
            if len(epi_runs) == 0:
                continue
            elif len(epi_runs) == 1:
                # use regular expression to remove the run value from the filename
                new_file_name = re.sub(r"_run-\w+_", "_", epi_runs[0])
                new_runs.append(new_file_name)
            else:
                # sort the epi runs by acquisition time
                epi_runs.sort(key=lambda x: get_acquisition_time(x))
                for i, epi_run in enumerate(epi_runs):
                    # use regular expression to replace the run value from the filename
                    new_file_name = re.sub(r"_run-\w+_", "_run-{:02d}_".format(i + 1), epi_run)
                    new_runs.append(new_file_name)
            for old_run, new_run in zip(epi_runs, new_runs):
                print("Renaming {} to {}".format(old_run, new_run))
                shutil.move(old_run, new_run)
                old_json = old_run.replace(".nii.gz", ".json")
                new_json = new_run.replace(".nii.gz", ".json")
                print("Renaming {} to {}".format(old_json, new_json))
                shutil.move(old_json, new_json)


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


def spin_echo_intended_for(subject_id, use_bids_uris, basename, image_file):
    # figure out the IntendedFor filename
    intended_for_kwargs = {"subject_id": subject_id, "bids_uris": use_bids_uris}
    set_intended_for = True
    if "fMRI" in basename:
        intended_for_kwargs["modality"] = "bold"
        intended_for_kwargs["folder"] = "func"
        intended_for_kwargs["task"] = basename.split("_")[1].lower()
        intended_for_kwargs["dir"] = basename.split("_")[2]
        if "rest" in intended_for_kwargs["task"]:
            intended_for_kwargs["run"] = intended_for_kwargs["task"].split("rest")[1]
            intended_for_kwargs["task"] = "rest"
    elif "PCASL" in basename:
        intended_for_kwargs["modality"] = "asl"
        intended_for_kwargs["folder"] = "perf"
        intended_for_kwargs["dir"] = "PA"
    elif "T1w" in basename:
        intended_for_kwargs["modality"] = "T1w"
        intended_for_kwargs["folder"] = "anat"
    elif "T2w" in basename:
        intended_for_kwargs["modality"] = "T2w"
        intended_for_kwargs["folder"] = "anat"
    else:
        warnings.warn("Unknown IntendedFor modality: {}. "
                      "Not setting IntendedFor field for {}".format(basename, image_file))
        set_intended_for = False
    if set_intended_for:
        return generate_intended_for(**intended_for_kwargs)
    else:
        return None


def run(wildcard, use_bids_uris=False, pe_dirs=("AP", "PA"), output_dir=".", method="hardlink", overwrite=False,
        dry_run=False, name="auto", grad_unwarp=False, skip_bias=True, t1w_use_derived=False, t2w_use_derived=False,
        skip=()):
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
                         intended_for=intended_for, **kwargs)

    first_subject_id = os.path.basename(subject_folders[0]).split("_")[0]
    write_bids_dataset_metadata_files(output_dir, name=get_dataset_name(name, first_subject_id))
    if not dry_run:
        fix_epi_runs(output_dir)


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
