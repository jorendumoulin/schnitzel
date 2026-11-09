connect
targets -set -nocase -filter {name =~ "PSU"}
source /home/joren/phd/schnitzel/build/vivado-synth/schnitzel_kv260.gen/sources_1/bd/design_1/ip/design_1_zynq_ultra_ps_e_0_0/psu_init.tcl
psu_init
psu_post_config
psu_ps_pl_reset_config
psu_ps_pl_isolation_removal
targets
exit
