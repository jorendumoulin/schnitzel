# Program the KV260 bitstream, initialize the MPSoC PS/PL clocks, and attach
# the matching ILA probes.  The PS-generated PL clock is not guaranteed to be
# running immediately after JTAG configuration, so the XSDB initialization is
# intentionally between programming and the final Hardware Manager refresh.

set bit /home/joren/phd/schnitzel/build/vivado-synth/schnitzel_kv260.runs/impl_1/design_1_wrapper.bit
set ltx /home/joren/phd/schnitzel/build/vivado-synth/schnitzel_kv260.runs/impl_1/design_1_wrapper.ltx
set psinit /home/joren/phd/schnitzel/fpga/init_ps.tcl
set xsdb /home/joren/vivado/2026.1/Vitis/bin/xsdb

open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set tgt [lindex [get_hw_targets] 0]
set_property PARAM.FREQUENCY 15000000 $tgt
set dev [get_hw_devices xck26_0]
set_property PROGRAM.FILE $bit $dev
set_property PROBES.FILE $ltx $dev
program_hw_devices $dev
close_hw_manager

if {[catch {exec $xsdb $psinit} err]} {
  error "PS initialization failed: $err"
}

open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set tgt [lindex [get_hw_targets] 0]
set_property PARAM.FREQUENCY 15000000 $tgt
set dev [get_hw_devices xck26_0]
set_property PROBES.FILE $ltx $dev
refresh_hw_device $dev
puts "Detected ILA cores: [get_hw_ilas -of_objects $dev]"
