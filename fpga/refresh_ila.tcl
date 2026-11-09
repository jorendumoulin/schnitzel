open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set tgt [lindex [get_hw_targets] 0]
set_property PARAM.FREQUENCY 15000000 $tgt
set dev [get_hw_devices xck26_0]
set ltx /home/joren/phd/schnitzel/build/vivado-synth/schnitzel_kv260.runs/impl_1/design_1_wrapper.ltx
set_property PROBES.FILE $ltx $dev
refresh_hw_device $dev
puts "BSCAN=[get_property BSCAN_SWITCH_USER_MASK $dev]"
puts "HW_ILAS=[get_hw_ilas -of_objects $dev]"
close_hw_manager
