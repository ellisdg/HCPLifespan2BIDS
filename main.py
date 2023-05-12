import argparse
import os
import glob
import shutil


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


def move_to_bids(image_file, bids_dir, subject_id, modality, method="hardlink", overwrite=False, dryrun=False,
                 **kwargs):
    if modality in ["T1w", "T2w"]:
        folder = "anat"
    elif modality == "bold":
        folder = "func"
    elif modality == "dwi":
        folder = "dwi"
    else:
        raise ValueError("Unknown modality: {}".format(modality))
    args = ["sub-{}".format(subject_id)]
    for key, value in kwargs.items():
        args.append("{}-{}".format(key, value))
    args.append(modality)
    output_file = os.path.join(bids_dir, "sub-{}".format(subject_id), folder, "_".join(args) + ".nii.gz")
    json_sidecar = image_file.replace(".nii.gz", ".json")
    output_json_sidecar = output_file.replace(".nii.gz", ".json")

    if os.path.exists(output_file) and not overwrite:
        print("File already exists: {}".format(output_file))
        return
    elif os.path.exists(output_file) and overwrite:
        print("Overwriting file: {}".format(output_file))
        if not dryrun:
            os.remove(output_file)
            os.remove(json_sidecar)

    print_text = "{} --> {}".format(image_file, output_file)

    if not dryrun:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if method == "hardlink":
        print("Creating hardlink: {}".format(print_text))
        if not dryrun:
            os.link(image_file, output_file)
            os.link(json_sidecar, output_json_sidecar)
    elif method == "symlink":
        print("Creating symlink: {}".format(print_text))
        if not dryrun:
            os.symlink(image_file, output_file)
            os.link(json_sidecar, output_json_sidecar)
    elif method == "copy":
        print("Copying file: {}".format(print_text))
        if not dryrun:
            shutil.copy(image_file, output_file)
            os.link(json_sidecar, output_json_sidecar)
    elif method == "move":
        print("Moving file: {}".format(print_text))
        if not dryrun:
            shutil.move(image_file, output_file)
            os.link(json_sidecar, output_json_sidecar)
    else:
        raise ValueError("Unknown method: {}".format(method))


def main():
    args = parse_args()

    subject_folders = glob.glob(os.path.join(args.nda_dir, "imagingcollection01/HC*"))
    for subject_folder in subject_folders:
        subject_id = os.path.basename(subject_folder).split("_")[0]

        image_files = glob.glob(os.path.join(subject_folder, "unprocessed/*.nii.gz"))
        for image_file in image_files:
            if "T1w" in image_file:
                bids_modality = "T1w"
            elif "T2w" in image_file:
                bids_modality = "T2w"
            elif "fMRI" in image_file:
                bids_modality = "bold"
            elif "Diffusion" in image_file:
                bids_modality = "dwi"
            else:
                bids_modality = None
                print("Unknown modality: {}".format(image_file))
            move_to_bids(image_file=image_file, bids_dir=args.output_dir, subject_id=subject_id,
                         modality=bids_modality, method=args.method, overwrite=args.overwrite, dryrun=args.dry_run)


if __name__ == "__main__":
    main()
