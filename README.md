# HCPLifespan2BIDS

Converts the unprocessed imaging data for the HCP Aging and Development studies to BIDS format.

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
* --use_bids_uris: If specified, will use BIDS URIs instead of BIDS filenames.

## Appendix: Downloading the data
I found it easiest to use the ndatools `downloadcmd` to download the data.


## Useful Links
* [suyashdb/hcp2bids](https://github.com/suyashdb/hcp2bids)
* [Phase encoding direction discussion](https://github.com/suyashdb/hcp2bids/issues/16)
* [Russ Poldrack asking about HCP BIDS data on Twitter/X](https://twitter.com/russpoldrack/status/1300877693957726208?lang=en)
* [Neurostars question asking about JSON sidecar files for HCPYA](https://neurostars.org/t/fmriprep-hcp-data-fieldmap-correction-looks-inverted/25867).
  (I think the metadata presented is not totally accurate.)
* [Partial conversion script for converting the HCPYA data to BIDS](https://github.com/datalad-datasets/hcp-functional-connectivity/pull/1/commits/e02970aab710a9c006c12be9cf5b442cc06d1f16)
* [Neurostars question asking for HCP BIDS data](https://neurostars.org/t/unprocessed-hcp-data-in-bids-format-for-fmriprep/24767/4)