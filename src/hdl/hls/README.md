# HLS spike - fixed-stack TMM

This is a **numerical and synthesis spike**, not the production kernel. It
implements a fixed 2-period Si/SiO2 stack at 1550 nm with fixed indices and
thicknesses. The phase trig is float; the matrix chain and reflectance use
`ap_fixed<32,8>` with `ap_fixed<48,16>` intermediates.

## Run

From this directory:

```powershell
& "C:\Xilinx\Vitis_HLS\2023.2\bin\vitis_hls.bat" -f run_hls.tcl
```

The script C-simulates against a double-precision reference, then synthesizes
for `xc7z020clg400-1` at a 10 ns clock. Build output is written under
`tmm_hls/` and is git-ignored.

## Result (2026-10-29, Vitis HLS 2023.2)

| Check | Result |
|---|---|
| C-simulation max absolute error vs double | `1.373e-7` (501 points) |
| Initiation interval | `1` |
| Iteration latency | `177` cycles |
| Estimated Fmax | `136.99 MHz` at 10 ns target |
| DSP | `192 / 220` (`87%`) |
| LUT | `43,317 / 53,200` (`81%`) |
| FF | `42,548 / 106,400` (`39%`) |
| BRAM | `8 / 280` (`2%`) |

## Interpretation

- **G1 numerical equivalence: pass.** Fixed-point TMM can match double
  precision to well below the `1e-3` gate.
- **G2 timing: pass.** `II=1` was achieved.
- **G2 resource scalability: fail on Zynq-7020.** A 2-period stack consumes
  almost all DSPs and most LUTs, so it cannot scale to the 32-layer cap on this
  part.
- **Do not claim FPGA capability.** The spike is evidence for the decision, not
  a product result.

The dominant costs are the float `sin/cos` implementation and the fully
unrolled matrix chain (31 multipliers and two dividers in the report). Next
options, in order of likely value:

1. Replace float trig with fixed-point CORDIC or a small LUT.
2. Share/time-multiplex complex multipliers instead of fully unrolling.
3. Reduce intermediate precision or use a sequential matrix chain.
4. Re-target a larger UltraScale+ device if batch throughput justifies it.
5. Compare against a GPU or surrogate implementation before committing to FPGA.

The CPU kernel already handles the interactive SME use case; the FPGA business
case is batch throughput, power, or embedded deployment.
