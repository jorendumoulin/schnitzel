# Flatten Ibex to a single file, loosely based on https://github.com/ucb-bar/ibex-wrapper

dir := $(abspath .)
ibex := $(dir)/ibex

FLATTENED_VERILOG := IbexWrapperFlattened.sv

.PHONY: default clean
default: $(FLATTENED_VERILOG)

IBEX_PKGS := \
	$(ibex)/rtl/ibex_pkg.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_assert.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_ram_1p_pkg.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_cipher_pkg.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_pkg.sv \
	$(ibex)/dv/uvm/core_ibex/common/prim/prim_pkg.sv

IBEX_VSRCS := \
	$(ibex)/rtl/ibex_alu.sv \
	$(ibex)/rtl/ibex_branch_predict.sv \
	$(ibex)/rtl/ibex_compressed_decoder.sv \
	$(ibex)/rtl/ibex_controller.sv \
	$(ibex)/rtl/ibex_core.sv \
	$(ibex)/rtl/ibex_counter.sv \
	$(ibex)/rtl/ibex_cs_registers.sv \
	$(ibex)/rtl/ibex_csr.sv \
	$(ibex)/rtl/ibex_decoder.sv \
	$(ibex)/rtl/ibex_dummy_instr.sv \
	$(ibex)/rtl/ibex_ex_block.sv \
	$(ibex)/rtl/ibex_fetch_fifo.sv \
	$(ibex)/rtl/ibex_icache.sv \
	$(ibex)/rtl/ibex_id_stage.sv \
	$(ibex)/rtl/ibex_if_stage.sv \
	$(ibex)/rtl/ibex_load_store_unit.sv \
	$(ibex)/rtl/ibex_lockstep.sv \
	$(ibex)/rtl/ibex_multdiv_fast.sv \
	$(ibex)/rtl/ibex_multdiv_slow.sv \
	$(ibex)/rtl/ibex_pmp.sv \
	$(ibex)/rtl/ibex_prefetch_buffer.sv \
	$(ibex)/rtl/ibex_register_file_ff.sv \
	$(ibex)/rtl/ibex_register_file_fpga.sv \
	$(ibex)/rtl/ibex_register_file_latch.sv \
	$(ibex)/rtl/ibex_top.sv \
	$(ibex)/rtl/ibex_wb_stage.sv \
	$(ibex)/dv/uvm/core_ibex/common/prim/prim_clock_gating.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_gating.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_39_32_enc.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_39_32_dec.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_lfsr.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_28_22_enc.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_28_22_dec.sv \
	$(ibex)/dv/uvm/core_ibex/common/prim/prim_ram_1p.sv \
	$(ibex)/dv/uvm/core_ibex/common/prim/prim_buf.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_ram_1p.sv \
	$(ibex)/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_buf.sv

IBEX_WRAPPER := $(dir)/IbexWrapper.sv

IBEX_SRCS := $(IBEX_PKGS) $(IBEX_VSRCS) $(IBEX_WRAPPER)

IBEX_INCLUDES := \
	-I$(ibex)/vendor/lowrisc_ip/ip/prim/rtl \
	-I$(ibex)/formal/data_ind_timing \
	-I$(ibex)/vendor/lowrisc_ip/dv/sv/dv_utils

# Flatten Ibex to a single file using verilog, comment out all resulting ` line references.
$(FLATTENED_VERILOG): $(IBEX_SRCS)
	verilator -sv -E $(IBEX_INCLUDES) $(IBEX_SRCS) > $@
	sed -i '/^`/s/^/\/\//' $@

clean:
	rm -f $(FLATTENED_VERILOG)
