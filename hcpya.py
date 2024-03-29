# Converting from HCP-YA to BIDS
# Conversion of the HCP-Young Adult (HCP-YA) dataset to BIDS is a bit different from the Lifespan datasets
# shared by the NDA.
# The dataset is shared by the CCF (Connectome Coordination Facility) which used a slightly different
# convention for the file names and folder structure.
from lifespan import create_parser, run
import os

# T1w images - get from T1w/t1w_acpc_dc.nii.gz
# T2w images - get from T1w/t2w_acpc_dc.nii.gz
# DWI images - get from Diffusion/data.nii.gz

# The fmri images need to first be preprocessed using the gradunwarp tool
# The spinecho fieldmaps and sbref files also need to be preprocessed using the gradunwarp tool
# fMRI images - get from gradunwarp/tfMRI/tfMRI*/tfMRI*.nii.gz


def parse_args():
    parser = create_parser()
    parser.add_argument("--hcp_dir", type=str, help="Path to the HCP-Young Adult dataset", required=True)
    parser.add_argument("--grad_unwarp", action="store_true",
                        help="Whether to use gradient unwarped data. This data must be computed beforehand.")
    # TODO: add gradient unwarped data for diffusion as well
    return parser.parse_args()


def main():
    args = parse_args()
    wildcard = os.path.join(args.hcp_dir, "*")
    run(wildcard=wildcard, use_bids_uris=args.use_bids_uris, pe_dirs=("LR", "RL"),  output_dir=args.output_dir,
        method=args.method, overwrite=args.overwrite, dry_run=args.dry_run, name="HCPYoungAdult",
        grad_unwarp=args.grad_unwarp, t1w_use_derived=True, t2w_use_derived=True,
        skip=("AFI.nii.gz", "FieldMap_Magnitude.nii.gz", "FieldMap_Phase.nii.gz", "7T/", "3T/Diffusion/", "3T_.nii.gz"),
        use_precompiled_sidecars=True, sort_by_run_name=True)


if __name__ == "__main__":
    main()
