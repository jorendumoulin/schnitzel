open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set dev [get_hw_devices xck26_0]
puts "DEVICE=$dev"
puts "BSCAN_PROPS=[lsearch -all -inline [list_property $dev] *BSCAN*]"
puts "DEBUG_PROPS=[lsearch -all -inline [list_property $dev] *DEBUG*]"
puts "HW_ILAS=[get_hw_ilas -of_objects $dev]"
close_hw_manager
