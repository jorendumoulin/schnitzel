# This script was generated automatically by bender.
if [ info exists search_path ] {{
  set search_path_initial $search_path
}}
set ROOT = "/home/joren/phd/schnitzel"

set search_path $search_path_initial
lappend search_path "$ROOT/submodules/cva6/common/local/util"
lappend search_path "$ROOT/submodules/cva6/core/include"
lappend search_path "$ROOT/submodules/cva6/vendor/pulp-platform/axi/include"
lappend search_path "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/include"
set_db init_hdl_search_path $search_path

read_hdl -language sv \
    -define { \
        TARGET_GENUS \
        TARGET_SYNTHESIS \
    } \
    [list \
        "$ROOT/submodules/cva6/core/include/config_pkg.sv" \
        "$ROOT/src/main/resources/cva6/cv64a6_imafdc_sv39_config_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/riscv_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/ariane_pkg.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/axi/src/axi_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/wt_cache_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/std_cache_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/instr_tracer_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/build_config_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/aes_pkg.sv" \
        "$ROOT/submodules/cva6/core/include/triggers_pkg.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_pkg.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/cf_math_pkg.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/fpga-support/rtl/SyncDpRam.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/fpga-support/rtl/AsyncDpRam.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/fpga-support/rtl/AsyncThreePortRam.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/fpga-support/rtl/SyncThreePortRam.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/fpga-support/rtl/SyncDpRam_ind_r_w.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_cast_multi.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_classifier.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/clk/rtl/gated_clk_cell.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_ctrl.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_ff1.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_pack_single.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_prepare.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_round_single.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_special.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_srt_single.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fdsu/rtl/pa_fdsu_top.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fpu/rtl/pa_fpu_dp.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fpu/rtl/pa_fpu_frbus.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/opene906/E906_RTL_FACTORY/gen_rtl/fpu/rtl/pa_fpu_src_type.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_ctrl.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_double.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_ff1.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_pack.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_prepare.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_round.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_scalar_dp.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_srt_radix16_bound_table.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_srt_radix16_with_sqrt.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_srt.v" \
        "$ROOT/submodules/cva6/core/cvfpu/vendor/openc910/C910_RTL_FACTORY/gen_rtl/vfdsu/rtl/ct_vfdsu_top.v" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_divsqrt_th_32.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_divsqrt_th_64_multi.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_divsqrt_multi.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_fma_multi.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_fma.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_noncomp.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_opgroup_block.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_opgroup_fmt_slice.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_opgroup_multifmt_slice.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_rounding.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpnew_top.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/defs_div_sqrt_mvp.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/control_mvp.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/div_sqrt_top_mvp.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/iteration_div_sqrt_mvp.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/norm_div_sqrt_mvp.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/nrbd_nrsc_mvp.sv" \
        "$ROOT/submodules/cva6/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/preprocess_mvp.sv" \
        "$ROOT/submodules/cva6/core/cvxif_compressed_if_driver.sv" \
        "$ROOT/submodules/cva6/core/cvxif_issue_register_commit_if_driver.sv" \
        "$ROOT/submodules/cva6/core/cvxif_fu.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/fifo_v3.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/lfsr.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/lfsr_8bit.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/stream_arbiter.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/stream_arbiter_flushable.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/stream_mux.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/stream_demux.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/lzc.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/rr_arb_tree.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/shift_reg.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/unread.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/popcount.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/exp_backoff.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/counter.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/common_cells/src/delta_counter.sv" \
        "$ROOT/submodules/cva6/core/cva6.sv" \
        "$ROOT/submodules/cva6/core/cva6_rvfi_probes.sv" \
        "$ROOT/submodules/cva6/core/alu.sv" \
        "$ROOT/submodules/cva6/core/alu_wrapper.sv" \
        "$ROOT/submodules/cva6/core/aes.sv" \
        "$ROOT/submodules/cva6/core/fpu_wrap.sv" \
        "$ROOT/submodules/cva6/core/branch_unit.sv" \
        "$ROOT/submodules/cva6/core/compressed_decoder.sv" \
        "$ROOT/submodules/cva6/core/macro_decoder.sv" \
        "$ROOT/submodules/cva6/core/controller.sv" \
        "$ROOT/submodules/cva6/core/zcmt_decoder.sv" \
        "$ROOT/submodules/cva6/core/csr_buffer.sv" \
        "$ROOT/submodules/cva6/core/csr_regfile.sv" \
        "$ROOT/submodules/cva6/core/trigger_module.sv" \
        "$ROOT/submodules/cva6/core/decoder.sv" \
        "$ROOT/submodules/cva6/core/ex_stage.sv" \
        "$ROOT/submodules/cva6/core/instr_realign.sv" \
        "$ROOT/submodules/cva6/core/id_stage.sv" \
        "$ROOT/submodules/cva6/core/issue_read_operands.sv" \
        "$ROOT/submodules/cva6/core/issue_stage.sv" \
        "$ROOT/submodules/cva6/core/load_unit.sv" \
        "$ROOT/submodules/cva6/core/load_store_unit.sv" \
        "$ROOT/submodules/cva6/core/lsu_bypass.sv" \
        "$ROOT/submodules/cva6/core/mult.sv" \
        "$ROOT/submodules/cva6/core/multiplier.sv" \
        "$ROOT/submodules/cva6/core/serdiv.sv" \
        "$ROOT/submodules/cva6/core/perf_counters.sv" \
        "$ROOT/submodules/cva6/core/ariane_regfile_ff.sv" \
        "$ROOT/submodules/cva6/core/ariane_regfile_fpga.sv" \
        "$ROOT/submodules/cva6/core/scoreboard.sv" \
        "$ROOT/submodules/cva6/core/raw_checker.sv" \
        "$ROOT/submodules/cva6/core/store_buffer.sv" \
        "$ROOT/submodules/cva6/core/amo_buffer.sv" \
        "$ROOT/submodules/cva6/core/store_unit.sv" \
        "$ROOT/submodules/cva6/core/commit_stage.sv" \
        "$ROOT/submodules/cva6/core/axi_shim.sv" \
        "$ROOT/submodules/cva6/core/cva6_accel_first_pass_decoder_stub.sv" \
        "$ROOT/submodules/cva6/core/acc_dispatcher.sv" \
        "$ROOT/submodules/cva6/core/cva6_fifo_v3.sv" \
        "$ROOT/submodules/cva6/core/frontend/btb.sv" \
        "$ROOT/submodules/cva6/core/frontend/bht.sv" \
        "$ROOT/submodules/cva6/core/frontend/bht2lvl.sv" \
        "$ROOT/submodules/cva6/core/frontend/ras.sv" \
        "$ROOT/submodules/cva6/core/frontend/instr_scan.sv" \
        "$ROOT/submodules/cva6/core/frontend/instr_queue.sv" \
        "$ROOT/submodules/cva6/core/frontend/frontend.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/wt_dcache_ctrl.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/wt_dcache_mem.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/wt_dcache_missunit.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/wt_dcache_wbuffer.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/wt_dcache.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/cva6_icache.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/wt_cache_subsystem.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/wt_axi_adapter.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/tag_cmp.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/axi_adapter.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/miss_handler.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/cache_ctrl.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/cva6_icache_axi_wrapper.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/std_cache_subsystem.sv" \
        "$ROOT/submodules/cva6/core/cache_subsystem/std_nbdcache.sv" \
        "$ROOT/submodules/cva6/common/local/util/instr_tracer.sv" \
        "$ROOT/submodules/cva6/common/local/util/tc_sram_wrapper.sv" \
        "$ROOT/submodules/cva6/common/local/util/tc_sram_wrapper_cache_techno.sv" \
        "$ROOT/submodules/cva6/vendor/pulp-platform/tech_cells_generic/src/rtl/tc_sram.sv" \
        "$ROOT/submodules/cva6/common/local/util/sram.sv" \
        "$ROOT/submodules/cva6/common/local/util/sram_cache.sv" \
        "$ROOT/submodules/cva6/core/pmp/src/pmp.sv" \
        "$ROOT/submodules/cva6/core/pmp/src/pmp_entry.sv" \
        "$ROOT/submodules/cva6/core/pmp/src/pmp_data_if.sv" \
        "$ROOT/submodules/cva6/core/cva6_mmu/cva6_mmu.sv" \
        "$ROOT/submodules/cva6/core/cva6_mmu/cva6_ptw.sv" \
        "$ROOT/submodules/cva6/core/cva6_mmu/cva6_tlb.sv" \
        "$ROOT/submodules/cva6/core/cva6_mmu/cva6_shared_tlb.sv" \
    ]

set search_path $search_path_initial
lappend search_path "$ROOT/submodules/ibex/dv/uvm/core_ibex/common/prim"
lappend search_path "$ROOT/submodules/ibex/formal/data_ind_timing"
lappend search_path "$ROOT/submodules/ibex/vendor/lowrisc_ip/dv/sv/dv_utils"
lappend search_path "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl"
set_db init_hdl_search_path $search_path

read_hdl -language sv \
    -define { \
        TARGET_GENUS \
        TARGET_SYNTHESIS \
    } \
    [list \
        "$ROOT/submodules/ibex/dv/uvm/core_ibex/common/prim/prim_pkg.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_ram_1p_pkg.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_cipher_pkg.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_pkg.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_mubi_pkg.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_count_pkg.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_util_pkg.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_pkg.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_assert.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_buf.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_gating.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_ram_1p.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_flop.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_mux2.sv" \
        "$ROOT/submodules/ibex/dv/uvm/core_ibex/common/prim/prim_buf.sv" \
        "$ROOT/submodules/ibex/dv/uvm/core_ibex/common/prim/prim_clock_gating.sv" \
        "$ROOT/submodules/ibex/dv/uvm/core_ibex/common/prim/prim_ram_1p.sv" \
        "$ROOT/submodules/ibex/dv/uvm/core_ibex/common/prim/prim_flop.sv" \
        "$ROOT/submodules/ibex/dv/uvm/core_ibex/common/prim/prim_clock_mux2.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_28_22_enc.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_28_22_dec.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_39_32_enc.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_39_32_dec.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_inv_39_32_enc.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_inv_39_32_dec.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_lfsr.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_count.sv" \
        "$ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_ram_1p_scr.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_alu.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_branch_predict.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_compressed_decoder.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_controller.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_core.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_counter.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_cs_registers.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_csr.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_decoder.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_dummy_instr.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_ex_block.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_fetch_fifo.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_icache.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_id_stage.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_if_stage.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_load_store_unit.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_lockstep.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_multdiv_fast.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_multdiv_slow.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_pmp.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_prefetch_buffer.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_wb_stage.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_register_file_ff.sv" \
        "$ROOT/submodules/ibex/rtl/ibex_top.sv" \
    ]

set search_path $search_path_initial
set_db init_hdl_search_path $search_path

read_hdl -language sv \
    -define { \
        TARGET_GENUS \
        TARGET_SYNTHESIS \
    } \
    [list \
        "$ROOT/generated/AXIDemux.sv" \
        "$ROOT/generated/AXIMux.sv" \
        "$ROOT/generated/AffineAgu.sv" \
        "$ROOT/generated/AffineAgu_1.sv" \
        "$ROOT/generated/AffineAgu_2.sv" \
        "$ROOT/generated/AffineAgu_4.sv" \
        "$ROOT/generated/AluAccelerator.sv" \
        "$ROOT/generated/AluArray.sv" \
        "$ROOT/generated/AluPE.sv" \
        "$ROOT/generated/AxiToMem.sv" \
        "$ROOT/generated/AxiToMem_1.sv" \
        "$ROOT/generated/CVA6.sv" \
        "$ROOT/generated/Cluster.sv" \
        "$ROOT/generated/Core.sv" \
        "$ROOT/generated/Core_1.sv" \
        "$ROOT/generated/CsrCombiner.sv" \
        "$ROOT/generated/CsrDemux.sv" \
        "$ROOT/generated/CsrInterface.sv" \
        "$ROOT/generated/CsrInterface_1.sv" \
        "$ROOT/generated/DecoupledIOToAXI.sv" \
        "$ROOT/generated/DecoupledIOToAXI_1.sv" \
        "$ROOT/generated/Dma.sv" \
        "$ROOT/generated/GlobalBarrier.sv" \
        "$ROOT/generated/HWBarrier.sv" \
        "$ROOT/generated/InstructionCache.sv" \
        "$ROOT/generated/Interconnect.sv" \
        "$ROOT/generated/MemDemux.sv" \
        "$ROOT/generated/MemWidthConverter.sv" \
        "$ROOT/generated/Queue1_Vec16_UInt32.sv" \
        "$ROOT/generated/Queue1_Vec32_UInt64.sv" \
        "$ROOT/generated/Queue1_Vec4_UInt32.sv" \
        "$ROOT/generated/Queue1_Vec8_UInt64.sv" \
        "$ROOT/generated/Queue2_DataQueue.sv" \
        "$ROOT/generated/Queue2_DataQueue_1.sv" \
        "$ROOT/generated/Queue32_Bool.sv" \
        "$ROOT/generated/Queue3_Streamer_Anon.sv" \
        "$ROOT/generated/Queue3_UInt32.sv" \
        "$ROOT/generated/Queue3_UInt64.sv" \
        "$ROOT/generated/Queue6_Streamer_Anon.sv" \
        "$ROOT/generated/Queue6_UInt32.sv" \
        "$ROOT/generated/Queue6_UInt64.sv" \
        "$ROOT/generated/RRArbiter2_BChan.sv" \
        "$ROOT/generated/RRArbiter2_BusReq.sv" \
        "$ROOT/generated/RRArbiter2_BusReq_56.sv" \
        "$ROOT/generated/RRArbiter2_Meta.sv" \
        "$ROOT/generated/RRArbiter2_Meta_1.sv" \
        "$ROOT/generated/RRArbiter2_RChan.sv" \
        "$ROOT/generated/RRArbiter30_BusReq.sv" \
        "$ROOT/generated/RRArbiter4_ARChan.sv" \
        "$ROOT/generated/RRArbiter4_AWChan.sv" \
        "$ROOT/generated/RRArbiter58_BusReq.sv" \
        "$ROOT/generated/Streamer.sv" \
        "$ROOT/generated/Streamer_1.sv" \
        "$ROOT/generated/Streamer_3.sv" \
        "$ROOT/generated/TensorCluster.sv" \
        "$ROOT/generated/TensorCore.sv" \
        "$ROOT/generated/Top.sv" \
        "$ROOT/generated/cva6_wrapper.sv" \
        "$ROOT/generated/data_sram_sram_64x32.sv" \
        "$ROOT/generated/ibex_wrapper.sv" \
        "$ROOT/generated/ram_2x36.sv" \
        "$ROOT/generated/ram_2x576.sv" \
        "$ROOT/generated/ram_32x1.sv" \
        "$ROOT/generated/ram_3x32.sv" \
        "$ROOT/generated/ram_3x64.sv" \
        "$ROOT/generated/ram_3x96.sv" \
        "$ROOT/generated/ram_6x32.sv" \
        "$ROOT/generated/ram_6x64.sv" \
        "$ROOT/generated/ram_6x96.sv" \
        "$ROOT/generated/tags_sram_sram_64x20.sv" \
        "$ROOT/generated/tcdm_ports_srams_sram_1024x32.sv" \
        "$ROOT/generated/tcdm_srams_sram_1024x64.sv" \
    ]

set search_path $search_path_initial
