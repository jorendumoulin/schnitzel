# 2026-09-07T13:47:53.914004222
import vitis

client = vitis.create_client()
client.set_workspace(path="fpga")

platform = client.create_platform_component(name = "platform",hw_design = "$COMPONENT_LOCATION/../../build/vivado-synth/design_1_wrapper.xsa",os = "standalone",cpu = "psu_cortexa53_0",domain_name = "standalone_psu_cortexa53_0",architecture = "64-bit",compiler = "gcc")

comp = client.create_app_component(name="hello_world",platform = "$COMPONENT_LOCATION/../platform/export/platform/platform.xpfm",domain = "standalone_psu_cortexa53_0",template = "hello_world")

vitis.dispose()

