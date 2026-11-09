# Vivado implementation post-opt_design hook.
#
# The MPSoC PL clock used by this design is 50 MHz.  Vivado 2026.1 can
# otherwise give the automatically inserted debug hub its 300 MHz default,
# which prevents Hardware Manager from discovering the hub on the KV260.
# This hook runs after opt_design has inserted dbg_hub and before placement.

set hubs [get_debug_cores dbg_hub -quiet]
if {[llength $hubs] != 0} {
    set hub [lindex $hubs 0]
    set clocks [get_clocks clk_pl_0 -quiet]
    if {[llength $clocks] != 0} {
        set period_ns [get_property PERIOD [lindex $clocks 0]]
        set freq_hz [expr {round(1.0e9 / $period_ns)}]
    } else {
        # Keep this fallback conservative if the clock is not named clk_pl_0.
        set freq_hz 50000000
    }
    set_property C_CLK_INPUT_FREQ_HZ $freq_hz $hub
    puts "Configured dbg_hub input clock to ${freq_hz} Hz"
}
