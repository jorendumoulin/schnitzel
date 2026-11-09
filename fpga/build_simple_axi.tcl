# Build the standalone Scala AXI-Lite client for the KV260.
# Usage: vivado -mode batch -source fpga/build_simple_axi.tcl -tclargs <packaged-ip-dir> <project-dir>
set root [file normalize [file join [file dirname [info script]] ..]]
if {[llength $argv] < 1} { error "Usage: build_simple_axi.tcl <packaged-ip-dir> ?project-dir?" }
set ip_dir [file normalize [lindex $argv 0]]
set out [expr {[llength $argv] > 1 ? [file normalize [lindex $argv 1]] : [file join $root build simple-axi]}]
set ip_root [file join $ip_dir SimpleAxiClient]
if {![file exists [file join $ip_root component.xml]]} { error "Packaged SimpleAxiClient IP not found: [file join $ip_root component.xml]" }

create_project simple_axi_bd $out -part xck26-sfvc784-2LV-c -force
set_property board_part xilinx.com:kv260_som:part0:1.4 [current_project]
set_property ip_repo_paths [list $ip_root] [current_project]
update_ip_catalog

source [file join $root fpga simple_axi_block_design.tcl]
set bd [get_files -quiet [file join $out simple_axi_bd.srcs sources_1 bd design_1 design_1.bd]]
if {[llength $bd] != 1} { error "Could not find root block design" }
validate_bd_design
save_bd_design
generate_target all $bd
catch { make_wrapper -files $bd -top } wrapper_result
set wrapper [file join $out simple_axi_bd.gen sources_1 bd design_1 hdl design_1_wrapper.v]
if {![file exists $wrapper]} { error "Wrapper was not generated: $wrapper" }
add_files -norecurse $wrapper
set_property top design_1_wrapper [current_fileset]
update_compile_order -fileset sources_1

launch_runs synth_1 -jobs 1
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "SYNTH_STATUS=$synth_status"
if {![string match {*Complete*} $synth_status]} { error "Synthesis failed: $synth_status" }

launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "IMPL_STATUS=$impl_status"
if {![string match {*Complete*} $impl_status]} { error "Implementation failed: $impl_status" }

close_project
exit
