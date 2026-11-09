# Package the standalone Scala AXI-Lite peripheral as a small Vivado IP.
# Usage: vivado -mode batch -source fpga/package_simple_axi.tcl -tclargs <out-dir>

set root [file normalize [file join [file dirname [info script]] ..]]
set out [expr {[llength $argv] ? [file normalize [lindex $argv 0]] : [file join $root build SimpleAxiClient-ip]}]
set rtl [file join $out rtl]
set pack_project [file join $out packaging-project]
set ip_root [file join $out SimpleAxiClient]

file mkdir $out
file delete -force $rtl $pack_project $ip_root
cd $root
if {[catch {exec ./mill schnitzel.runMain sim.EmitVerilog --top=simple-axi --output-dir=$rtl 2>@1} message]} {
    puts stderr $message
    error "SimpleAxiClient RTL generation failed"
}

create_project -force SimpleAxiClient_pack $pack_project -part xck26-sfvc784-2LV-c
set_property source_mgmt_mode None [current_project]
foreach source [glob -nocomplain -directory $rtl *.sv] {
    add_files -norecurse $source
}
set_property top SimpleAxiClient [current_fileset]
update_compile_order -fileset sources_1

ipx::package_project -root_dir $ip_root \
    -vendor user.org \
    -library user \
    -taxonomy /UserIP \
    -import_files \
    -force

set core [ipx::current_core]
set_property name SimpleAxiClient $core
set_property version 1.0 $core
set_property display_name SimpleAxiClient_v1_0 $core
set_property description {Minimal Scala AXI4-Lite register peripheral} $core

foreach busif [ipx::get_bus_interfaces -of_objects $core] {
    ipx::remove_bus_interface [get_property name $busif] $core
}

proc add_map {busif logical physical} {
    set map [ipx::add_port_map $logical $busif]
    set_property physical_name $physical $map
}
proc add_axi_bus {core name mode maps} {
    set bus [ipx::add_bus_interface $name $core]
    set_property bus_type_vlnv xilinx.com:interface:aximm:1.0 $bus
    set_property abstraction_type_vlnv xilinx.com:interface:aximm_rtl:1.0 $bus
    set_property interface_mode $mode $bus
    foreach pair $maps { add_map $bus [lindex $pair 0] [lindex $pair 1] }
    return $bus
}

set s_maps {
    {AWADDR s_axi_aw_bits_addr} {AWPROT s_axi_aw_bits_prot} {AWVALID s_axi_aw_valid}
    {AWREADY s_axi_aw_ready} {WDATA s_axi_w_bits_data} {WSTRB s_axi_w_bits_strb}
    {WVALID s_axi_w_valid} {WREADY s_axi_w_ready} {BRESP s_axi_b_bits}
    {BVALID s_axi_b_valid} {BREADY s_axi_b_ready} {ARADDR s_axi_ar_bits_addr}
    {ARPROT s_axi_ar_bits_prot} {ARVALID s_axi_ar_valid} {ARREADY s_axi_ar_ready}
    {RDATA s_axi_r_bits_data} {RRESP s_axi_r_bits_resp} {RVALID s_axi_r_valid}
    {RREADY s_axi_r_ready}
}
set s_axi [add_axi_bus $core S_AXI_CTRL slave $s_maps]
set clk [ipx::add_bus_interface aclk $core]
set_property bus_type_vlnv xilinx.com:signal:clock:1.0 $clk
set_property abstraction_type_vlnv xilinx.com:signal:clock_rtl:1.0 $clk
set_property interface_mode slave $clk
add_map $clk CLK aclk
set p [ipx::add_bus_parameter ASSOCIATED_BUSIF $clk]
set_property value S_AXI_CTRL $p

set rst [ipx::add_bus_interface aresetn $core]
set_property bus_type_vlnv xilinx.com:signal:reset:1.0 $rst
set_property abstraction_type_vlnv xilinx.com:signal:reset_rtl:1.0 $rst
set_property interface_mode slave $rst
add_map $rst RST aresetn
set p [ipx::add_bus_parameter POLARITY $rst]
set_property value ACTIVE_LOW $p

ipx::save_core $core
ipx::check_integrity $core
close_project
puts "Packaged SimpleAxiClient IP: $ip_root/component.xml"
