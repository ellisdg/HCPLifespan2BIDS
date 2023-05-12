import argparse
import os
import glob
import shutil
import re


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nda_dir", type=str, required=True,
                        help="path to nda directory containing the unprocessed imagingcollection for the"
                             "HCP Aging or HCP Development datasets.")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="path to output BIDS directory.")
    parser.add_argument("--dry_run", action="store_true", help="do not write files, just print what would be done.")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing files.")
    parser.add_argument("--method", type=str, default="hardlink", choices=["hardlink", "symlink", "copy", "move"],
                        help="method to use for linking files.")
    return parser.parse_args()


def move_to_bids(image_file, bids_dir, subject_id, modality, folder, method="hardlink", overwrite=False, dryrun=False,
                 **kwargs):

    args = ["sub-{}".format(subject_id)]
    for key, value in kwargs.items():
        args.append("{}-{}".format(key, value))
    args.append(modality)
    output_file = os.path.join(bids_dir, "sub-{}".format(subject_id), folder, "_".join(args) + ".nii.gz")
    in_files = [image_file]
    out_files = [output_file]
    json_sidecar = image_file.replace(".nii.gz", ".json")
    if os.path.exists(json_sidecar):
        in_files.append(json_sidecar)
        out_files.append(output_file.replace(".nii.gz", ".json"))
    else:
        print("No JSON sidecar found for {}".format(image_file))

    if modality == "dwi":
        for in_file in in_files:
            # check for bval and bvec files
            bval_file = in_file.replace(".nii.gz", ".bval")
            bvec_file = in_file.replace(".nii.gz", ".bvec")
            if os.path.exists(bval_file):
                in_files.append(bval_file)
                out_files.append(output_file.replace(".nii.gz", ".bval"))
            if os.path.exists(bvec_file):
                in_files.append(bvec_file)
                out_files.append(output_file.replace(".nii.gz", ".bvec"))

    if os.path.exists(output_file) and not overwrite:
        print("File already exists: {}".format(output_file))
        return
    elif os.path.exists(output_file) and overwrite:
        print("Overwriting file: {}".format(output_file))
        if not dryrun:
            for file in out_files:
                os.remove(file)

    print_text = "{} --> {}".format(image_file, output_file)

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


def main():
    args = parse_args()

    subject_folders = glob.glob(os.path.join(args.nda_dir, "imagingcollection01/HC*"))
    for subject_folder in subject_folders:
        subject_id = os.path.basename(subject_folder).split("_")[0]

        image_files = glob.glob(os.path.join(subject_folder, "unprocessed/**.nii.gz"), recursive=True)
        for image_file in image_files:
            kwargs = dict()

            if "_AP" in image_file:
                kwargs["dir"] = "AP"
            elif "_PA" in image_file:
                kwargs["dir"] = "PA"

            if "SpinEchoFieldMap" in image_file:
                bids_modality = "epi"
                folder = "fmap"
                run = os.path.basename(os.path.dirname(image_file))
                if "_" in run:
                    run = run.split("_")[1]
                match = re.search(r"SpinEchoFieldMap(\d+)", image_file)
                if match:
                    run = run + match.group(1)
                kwargs["run"] = run
            elif "T1w" in image_file:
                folder = "anat"
                bids_modality = "T1w"
            elif "T2w" in image_file:
                folder = "anat"
                bids_modality = "T2w"
            elif "fMRI" in image_file:
                folder = "func"
                bids_modality = "bold"
            elif "Diffusion" in image_file:
                folder = "dwi"
                bids_modality = "dwi"
                # TODO: check which one comes first dir98 or dir99
                if "dir98" in image_file:
                    kwargs["run"] = "1"
                elif "dir99" in image_file:
                    kwargs["run"] = "2"
            elif "PCASL" in image_file:
                bids_modality = "asl"
                folder = "asl"
            else:
                folder = None
                bids_modality = None
                print("Unknown modality: {}".format(image_file))

            if "SBRef" in image_file:
                # overwrite the modality to be sbref
                bids_modality = "sbref"

            move_to_bids(image_file=image_file, bids_dir=args.output_dir, subject_id=subject_id, folder=folder,
                         modality=bids_modality, method=args.method, overwrite=args.overwrite, dryrun=args.dry_run,
                         **kwargs)


if __name__ == "__main__":
    main()
