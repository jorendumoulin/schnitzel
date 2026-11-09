# Package the generated FPGATop RTL as a Vivado IP.
#
# Usage (from the repository root):
#   vivado -mode batch -source fpga/package_ip.tcl \
#     -tclargs /path/to/ip-output
#
# The Bender-generated Vivado script supplies the complete, resolved source
# list and include paths. This script adds the interface metadata that allows
# Vivado SmartConnect to recognize the two AXI interfaces.

set root [file normalize [file join [file dirname [info script]] ..]]
set out [expr {[llength $argv] ? [file normalize [lindex $argv 0]] : [file join $root build FPGATop-ip]}]
set rtl [file join $root generated-fpga]
set bender_tcl [file join $out bender-vivado.tcl]
set pack_project [file join $out packaging-project]
set ip_root [file join $out FPGATop]

file mkdir $out
file delete -force $pack_project $ip_root

# Regenerate the Chisel output and resolved Vivado source script when this is
# run from the repository checkout. Existing generated files are overwritten.
cd $root
if {[catch {exec just generate-fpga-vivado generated-fpga $bender_tcl 2>@1} message]} {
    puts stderr $message
    error "FPGA RTL/Bender generation failed"
}

create_project -force FPGATop_pack $pack_project -part xck26-sfvc784-2LV-c
set_property source_mgmt_mode None [current_project]
source $bender_tcl
set_property top FPGATop [current_fileset]
update_compile_order -fileset sources_1

ipx::package_project -root_dir $ip_root \
    -vendor user.org \
    -library user \
    -taxonomy /UserIP \
    -import_files \
    -force

# Preserve the include hierarchy expected by CVA6/common_cells.
set packaged_regs [file join $ip_root src common_cells registers.svh]
file mkdir [file dirname $packaged_regs]
file copy -force [file join $root submodules cva6 vendor pulp-platform common_cells include common_cells registers.svh] $packaged_regs
foreach group_name {xilinx_anylanguagesynthesis xilinx_anylanguagebehavioralsimulation} {
    set group [ipx::get_file_groups $group_name -of_objects [ipx::current_core]]
    set include_file [ipx::add_file src/common_cells/registers.svh $group]
}

set core [ipx::current_core]
set_property name FPGATop $core
set_property version 1.0 $core
set_property display_name FPGATop_v1_0 $core
set_property description {This is the top of the schnitzel} $core

# Remove any inferred interface metadata. The generated Chisel names are
# intentionally mapped explicitly below.
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
    if {$mode eq "master"} {
        set_property interface_mode master $bus
    } else {
        set_property interface_mode slave $bus
    }
    foreach pair $maps {
        add_map $bus [lindex $pair 0] [lindex $pair 1]
    }
    return $bus
}

set m_maps {
    {AWID m_axi_aw_bits_id} {AWADDR m_axi_aw_bits_addr} {AWLEN m_axi_aw_bits_len}
    {AWSIZE m_axi_aw_bits_size} {AWBURST m_axi_aw_bits_burst} {AWLOCK m_axi_aw_bits_lock}
    {AWCACHE m_axi_aw_bits_cache} {AWPROT m_axi_aw_bits_prot} {AWQOS m_axi_aw_bits_qos}
    {AWREGION m_axi_aw_bits_region} {AWUSER m_axi_aw_bits_user} {AWVALID m_axi_aw_valid}
    {AWREADY m_axi_aw_ready} {WDATA m_axi_w_bits_data} {WSTRB m_axi_w_bits_strb}
    {WLAST m_axi_w_bits_last} {WUSER m_axi_w_bits_user} {WVALID m_axi_w_valid}
    {WREADY m_axi_w_ready} {BID m_axi_b_bits_id} {BRESP m_axi_b_bits_resp}
    {BUSER m_axi_b_bits_user} {BVALID m_axi_b_valid} {BREADY m_axi_b_ready}
    {ARID m_axi_ar_bits_id} {ARADDR m_axi_ar_bits_addr} {ARLEN m_axi_ar_bits_len}
    {ARSIZE m_axi_ar_bits_size} {ARBURST m_axi_ar_bits_burst} {ARLOCK m_axi_ar_bits_lock}
    {ARCACHE m_axi_ar_bits_cache} {ARPROT m_axi_ar_bits_prot} {ARQOS m_axi_ar_bits_qos}
    {ARREGION m_axi_ar_bits_region} {ARUSER m_axi_ar_bits_user} {ARVALID m_axi_ar_valid}
    {ARREADY m_axi_ar_ready} {RID m_axi_r_bits_id} {RDATA m_axi_r_bits_data}
    {RRESP m_axi_r_bits_resp} {RLAST m_axi_r_bits_last} {RUSER m_axi_r_bits_user}
    {RVALID m_axi_r_valid} {RREADY m_axi_r_ready}
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

set m_axi [add_axi_bus $core M_AXI_MEM master $m_maps]
set s_axi [add_axi_bus $core S_AXI_CTRL slave $s_maps]
proc set_bus_param {busif name value} {
    set param [ipx::add_bus_parameter $name $busif]
    set_property value $value $param
}
set_bus_param $m_axi NUM_READ_OUTSTANDING 1
set_bus_param $m_axi NUM_WRITE_OUTSTANDING 1
set_bus_param $s_axi NUM_READ_OUTSTANDING 1
set_bus_param $s_axi NUM_WRITE_OUTSTANDING 1
set mem_space [ipx::add_address_space M_AXI_MEM $core]
set_property range 0x10000000 $mem_space
set_property width 32 $mem_space
set_property master_address_space_ref M_AXI_MEM $m_axi

set clk [ipx::add_bus_interface aclk $core]
set_property bus_type_vlnv xilinx.com:signal:clock:1.0 $clk
set_property abstraction_type_vlnv xilinx.com:signal:clock_rtl:1.0 $clk
set_property interface_mode slave $clk
add_map $clk CLK aclk
set_bus_param $clk ASSOCIATED_RESET aresetn
set_bus_param $clk ASSOCIATED_BUSIF {S_AXI_CTRL:M_AXI_MEM}

set rst [ipx::add_bus_interface aresetn $core]
set_property bus_type_vlnv xilinx.com:signal:reset:1.0 $rst
set_property abstraction_type_vlnv xilinx.com:signal:reset_rtl:1.0 $rst
set_property interface_mode slave $rst
add_map $rst RST aresetn
set_bus_param $rst POLARITY ACTIVE_LOW

ipx::save_core $core
ipx::check_integrity $core
close_project
puts "Packaged FPGATop IP: $ip_root/component.xml"
