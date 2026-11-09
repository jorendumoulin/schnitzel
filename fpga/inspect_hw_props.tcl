open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set dev [get_hw_devices xck26_0]
foreach p {XSDB_USER_BSCAN BSCAN_SWITCH_USER_MASK USE_BSCAN_FALLBACK} {
  if {[catch {puts "$p=[get_property $p $dev]"} err]} { puts "$p=<error:$err>" }
}
close_hw_manager
