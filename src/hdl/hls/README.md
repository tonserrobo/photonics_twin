# HLS spike - fixed-stack TMM

This is a **numerical and synthesis spike**, not the production kernel. It
implements a fixed 2-period Si/SiO2 stack at 1550 nm with fixed indices and
thicknesses. The phase trig is float; the matrix chain and reflectance use
`ap_fixed<32,8>` with `ap_fixed<48,16>` intermediates.

## Run

From this directory:

```powershell
& "C:\Xilinx\Vitis_HLS\2023.2\bin\vitis_hls.bat" -f run_hls.tcl
& "C:\Xilinx\Vitis_HLS\2023.2\bin\vitis_hls.bat" -f run_hls_seq.tcl
```

Both scripts C-simulate against a double-precision reference, then synthesize
for `xc7z020clg400-1` at a 10 ns clock. The first fully unrolls the layer chain
(`II=1`); the second keeps it sequential (`II=4`). Build output is written under
`tmm_hls/` and `tmm_hls_seq/` and is git-ignored.

## Results (2026-10-29, Vitis HLS 2023.2)

| Check | Unrolled, II=1 | Sequential, II=4 |
|---|---:|---:|
| C-simulation max absolute error vs double | `1.373e-7` | `1.373e-7` |
| Iteration latency | `177` cycles | `190` cycles |
| Estimated Fmax | `136.99 MHz` | `136.99 MHz` |
| DSP | `192 / 220` (`87%`) | `127 / 220` (`57%`) |
| LUT | `43,317 / 53,200` (`81%`) | `48,156 / 53,200` (`90%`) |
| FF | `42,548 / 106,400` (`39%`) | `39,694 / 106,400` (`37%`) |
| BRAM | `8 / 280` (`2%`) | `8 / 280` (`2%`) |

## Interpretation

- **G1 numerical equivalence: pass.** Fixed-point TMM can match double
  precision to well below the `1e-3` gate.
- **G2 timing: pass for II=1.** The unrolled variant achieved `II=1`; the
  sequential variant reached `II=4`.
- **G2 resource scalability: fail on Zynq-7020.** The unrolled 2-period stack
  uses `87%` DSP and `81%` LUT; relaxing to `II=4` lowers DSP to `57%` but
  raises LUT to `90%`. Neither leaves room to scale to the 32-layer cap.
- **Do not claim FPGA capability.** The spike is evidence for the decision, not
  a product result.

The float `sin/cos` implementation and fixed-point operator width dominate
resources. Relaxing the unroll trades DSP for LUT rather than solving the
problem. Next options, in order of likely value:

1. Replace float trig with fixed-point CORDIC or a small LUT.
2. Reduce precision where the error budget allows.
3. Try a time-multiplexed state-machine architecture with an explicit II target.
4. Re-target a larger UltraScale+ device if batch throughput justifies it.
5. Compare against a GPU or surrogate implementation before committing to FPGA.

The CPU kernel already handles the interactive SME use case; the FPGA business
case is batch throughput, power, or embedded deployment.
