# [HCPLifespan2BIDS](https://github.com/ellisdg/HCPLifespan2BIDS)

Converts the unprocessed imaging data for the HCP Aging and Development (i.e. Lifespan) datasets to BIDS format.

## Usage

```
python main.py --nda_dir <path to unprocessed data> --output_dir <path to output BIDS directory>
```

## Options
You can run `python main.py --help` to see all options. The most important ones are:
* --nda_dir: Path to the unprocessed data directory. This should contain a directory titled 'imagingcollection01'.
* --output_dir: Path to the output BIDS directory. This directory will be created if it does not exist.
* --overwrite: If specified, will overwrite existing files in the output directory.
* --method: The method to use for linking/copying/moving the files. The options are "hardlink", "softlink", "copy", and "move". Default is "hardlink".
* --dry_run: If specified, will not actually copy/move/link any files, but will print out what it would do.
* --use_bids_uris: If specified, will use BIDS URIs instead of BIDS filenames in the JSON sidecar. This URIs are the current standard, but as of May 2023 they were not supported by fMRIPrep.

## Running fMRIPrep
I was able to sucessfully run fMRIPrep on the HCP-Development data after turning the bids verificaiton off.

## Downloading the data
I found it easiest to use the ndatools `downloadcmd` commandline tool to download the data. You can download `downloadcmd` using `pip install nda-tools`.
