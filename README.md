# [HCPLifespan2BIDS](https://github.com/ellisdg/HCPLifespan2BIDS)
Converts HCP datasets into BIDS format. Works for both Lifespan and HCPYA.
`lifespan.py`: Converts the unprocessed imaging data for the HCP Aging and Development (i.e. Lifespan) datasets to BIDS format.
`hcpya.py`: Converts the unprocessed imaging data for the HCP Young Adult dataset to BIDS format.

## Lifespan

### Usage

```
python lifepsan.py --nda_dir <path to unprocessed data> --output_dir <path to output BIDS directory>
```

### Options
You can run `python lifespan.py --help` to see all options. The most important ones are:
* --nda_dir: Path to the unprocessed data directory. This should contain a directory titled 'imagingcollection01'.
* --output_dir: Path to the output BIDS directory. This directory will be created if it does not exist.
* --overwrite: If specified, will overwrite existing files in the output directory.
* --method: The method to use for linking/copying/moving the files. 
The options are "hardlink", "softlink", "copy", and "move". Default is "hardlink".
* --dry_run: If specified, will not actually copy/move/link any files, but will print out what it would do.
* --use_bids_uris: If specified, will use BIDS URIs instead of BIDS filenames in the JSON sidecar. 
URIs are the current standard, but as of April 2024 they were not supported by fMRIPrep.

### Downloading the data
I found it easiest to use the ndatools `downloadcmd` commandline tool to download the data. You can download `downloadcmd` using `pip install nda-tools`.

## HCP Young Adult

TODO: Add information about the HCP Young Adult dataset.

## Running fMRIPrep
I was able to sucessfully run fMRIPrep on the HCP-Development and Young Adult data after turning the bids verification off.
I have not tested the Aging dataset yet.

## Useful Links
* [suyashdb/hcp2bids](https://github.com/suyashdb/hcp2bids)
* [Phase encoding direction discussion](https://github.com/suyashdb/hcp2bids/issues/16)
* [Russ Poldrack asking about HCP BIDS data on Twitter/X](https://twitter.com/russpoldrack/status/1300877693957726208?lang=en)
* [Neurostars question asking about JSON sidecar files for HCPYA](https://neurostars.org/t/fmriprep-hcp-data-fieldmap-correction-looks-inverted/25867).
  (PhaseEncodingDirection should be reversed from that provided by the asker.)
* [Partial conversion script for converting the HCPYA data to BIDS](https://github.com/datalad-datasets/hcp-functional-connectivity/pull/1/commits/e02970aab710a9c006c12be9cf5b442cc06d1f16)
* [Neurostars question asking for HCP BIDS data](https://neurostars.org/t/unprocessed-hcp-data-in-bids-format-for-fmriprep/24767/4)
* [Slice timing for HCPYA](https://wiki.humanconnectome.org/docs/HCP%20fMRI%20slice-timing%20acquisition%20parameters.html)
* [Diffusion readout time](https://neurostars.org/t/what-is-the-totalreadouttime-of-hcp-dwi-data/19622)

