# Vitis HLS spike: fixed-stack TMM kernel.
# Run from this directory:
#   vitis_hls -mode batch -source run_hls.tcl
#
# The target part is a Zynq-7020 for a reproducible baseline. Change it to the
# actual board before quoting resource numbers.
open_project -reset tmm_hls
set_top tmm_sweep_fixed
add_files tmm_hls.cpp
add_files -tb tmm_hls_tb.cpp
open_solution -reset "solution1" -flow_target vivado
set_part {xc7z020clg400-1}
create_clock -period 10 -name default

csim_design
csynth_design

exit
