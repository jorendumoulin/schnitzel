open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set tgt [lindex [get_hw_targets] 0]
set_property PARAM.FREQUENCY 15000000 $tgt
set dev [get_hw_devices xck26_0]
set bit /home/joren/phd/schnitzel/build/vivado-synth/schnitzel_kv260.runs/impl_1/design_1_wrapper.bit
set ltx /home/joren/phd/schnitzel/build/vivado-synth/schnitzel_kv260.runs/impl_1/design_1_wrapper.ltx
set_property PROGRAM.FILE $bit $dev
set_property PROBES.FILE $ltx $dev
if {[catch {set_property BSCAN_SWITCH_USER_MASK 0x1 $dev} err]} {
  puts "WARN: unable to set BSCAN_SWITCH_USER_MASK: $err"
}
puts "PROGRAM_FILE=[get_property PROGRAM.FILE $dev]"
puts "PROBES_FILE=[get_property PROBES.FILE $dev]"
program_hw_devices $dev
refresh_hw_device $dev
puts "HW_ILAS=[get_hw_ilas -of_objects $dev]"
close_hw_manager
