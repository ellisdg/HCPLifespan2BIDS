### Total Readout Time
Total readout time can be computed using the echo spacing and ReconMatrixPE:
TotalReadoutTime = EchoSpacing * (ReconMatrixPE - 1)

[source](https://neurostars.org/t/what-is-the-totalreadouttime-of-hcp-dwi-data/19622)

Using the scan parameters from the [HCPYA website](https://www.humanconnectome.org/storage/app/media/documentation/s1200/HCP_S1200_Release_Reference_Manual.pdf),
 we can compute the total readout time for each scan:
 * Diffusion: EchoSpacing = 0.00078s, ReconMatrixPE = 144, TotalReadoutTime = 0.00078 * (144 - 1) = 0.11154s
 * fMRI: EchoSpacing = 0.00058s, ReconMatrixPE = 90, TotalReadoutTime = 0.00058 * (90 - 1) = 0.05162s




