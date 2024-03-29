import glob
import json
import os
import re
import shutil
import warnings


def fix_epi_runs(bids_dir, pe_dirs, sort_by_run_name=False):
    """
    The epi runs must be renamed to match the BIDS standard
    The BIDS standard requires that the epi runs be named run-01, run-02, etc.
    instead of run-tasknameap, run-tasknamepa, etc.
    this script will assign each epi run a number according to the acquisition time of the volume
    the first run will be 1, the second run will be 2, etc.

    :param bids_dir: The bids directory
    :param pe_dirs: The phase encoding directions for the dataset
    :param sort_by_run_name: For the HCPYA dataset, we do not have acquisition times. This option will sort the runs by
    their task/run name instead.
    :return:
    """

    fmap_folders = glob.glob(os.path.join(bids_dir, "sub-*", "fmap"))
    for fmap_folder in fmap_folders:
        for dir in pe_dirs:  # this is a bit of a hack to just get the epi runs for the same direction
            epi_runs = glob.glob(os.path.join(fmap_folder, "*dir-{}*epi.nii.gz".format(dir)))
            new_runs = list()
            if len(epi_runs) == 0:
                continue
            elif len(epi_runs) == 1:
                # use regular expression to remove the run value from the filename
                new_file_name = re.sub(r"_run-\w+_", "_", epi_runs[0])
                new_runs.append(new_file_name)
            elif sort_by_run_name:
                # sort the epi runs by run name
                # get the run name using regular expression
                epi_runs.sort(key=lambda x: re.search(r"run-([a-zA-Z0-9]+)_", x).group(1))
                for i, epi_run in enumerate(epi_runs):
                    new_file_name = re.sub(r"_run-\w+_", "_run-{:02d}_".format(i + 1), epi_run)
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


def move_to_bids(image_file, bids_dir, subject_id, modality, folder, method="hardlink", overwrite=False, dryrun=False,
                 intended_for=None, exists_ok=True, use_precompiled_sidecars=False, **kwargs):
    output_file = generate_full_output_filename(bids_dir, subject_id, modality, folder, **kwargs)
    in_files = [image_file]
    out_files = [output_file]

    if use_precompiled_sidecars:
        # use predefined json sidecar files from this project
        # the sidcar files can be found under the "sidecars" directory
        json_sidecar = match_json_sidecar(output_file)
    else:
        json_sidecar = image_file.replace(".nii.gz", ".json")

    output_json_sidecar = output_file.replace(".nii.gz", ".json")

    if json_sidecar is not None and os.path.exists(json_sidecar):
        in_files.append(json_sidecar)
        out_files.append(output_json_sidecar)
    else:
        warnings.warn("JSON sidecar file does not exist: {}".format(json_sidecar))

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
        in_files, out_files = prep_bold_to_bids(image_file, bids_dir, subject_id, folder, in_files, out_files,
                                                output_file, overwrite=overwrite, dryrun=dryrun, **kwargs)

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


def prep_bold_to_bids(image_file, bids_dir, subject_id, folder, in_files, out_files, output_file,
                      overwrite=False, dryrun=False, **kwargs):
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
    return in_files, out_files


def match_json_sidecar(image_file):
    # get the task name from the filename
    try:
        task_name = re.search("task-([a-zA-Z0-9]+)_", image_file).group(1)
    except AttributeError:
        task_name = None

    # get the acquisition direction
    try:
        acq_dir = re.search("dir-([a-zA-Z0-9]+)_", image_file).group(1)
    except AttributeError:
        acq_dir = None

    # get the modality
    modality = image_file.split("_")[-1].split(".")[0]

    # find a matching sidecar file
    sidecar_basename = f"{modality}.json"
    if acq_dir is not None:
        sidecar_basename = f"dir-{acq_dir}_{sidecar_basename}"
    if task_name is not None:
        sidecar_basename = f"task-{task_name}_{sidecar_basename}"
    sidecar_filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "sidecars", sidecar_basename))

    if os.path.exists(sidecar_filename):
        return sidecar_filename


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


def convert_ev_dir(ev_dir, out_file):
    """
    HCP has the events in a directory called "EVs". This function converts the events to a BIDS compatible format.
    :param ev_dir: "EVs" directory in the HCP dataset.
    :param out_file: events file to be created with .tsv extension.
    :return: Location of the output file.
    """

    from pandas.errors import EmptyDataError
    import pandas as pd
    # TODO: figure out how to encode errors
    dfs = list()
    for ev in os.listdir(ev_dir):

        if ev in ("Sync.txt",) or ".txt" not in ev:
            continue
        try:
            df_ev = pd.read_csv(os.path.join(ev_dir, ev), delimiter="\t", header=None)
        except EmptyDataError:
            continue
        df_ev.columns = ["onset", "duration", "strength"]
        df_ev["trial_type"] = ev.split(".txt")[0]
        dfs.append(df_ev)

    df = pd.concat(dfs).sort_values("onset").set_index("onset")
    assert not os.path.exists(out_file)
    df.to_csv(out_file, sep="\t")

    return out_file
