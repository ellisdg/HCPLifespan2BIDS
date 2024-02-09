# Converting from HCP-YA to BIDS
# Conversion of the HCP-Young Adult (HCP-YA) dataset to BIDS is a bit different from the Lifespan datasets
# shared by the NDA.
# The dataset is shared by the CCF (Connectome Coordination Facility) which used a slightly different
# convention for the file names and folder structure.
from lifespan import create_parser, run
import os


def parse_args():
    parser = create_parser()
    parser.add_argument("--hcp_dir", type=str, help="Path to the HCP-Young Adult dataset")
    parser.add_argument("--grad_unwarp", action="store_true",
                        help="Whether to use gradient unwarped data. This data must be computed beforehand.")
    # TODO: add gradient unwarped data for diffusion as well
    return parser.parse_args()


def main():
    args = parse_args()
    wildcard = os.path.join(args.hcp_dir, "*/")
    run(wildcard=wildcard, use_bids_uris=args.use_bids_uris, pe_dirs=("LR", "RL"),  output_dir=args.output_dir,
        method=args.method, overwrite=args.overwrite, dry_run=args.dry_run, name="HCPYoungAdult",
        grad_unwarp=args.grad_unwarp)


if __name__ == "__main__":
    main()
