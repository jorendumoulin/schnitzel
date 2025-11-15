// Simple wrapper exposing useful ports and configuring Ibex parameters to the 'small' configuration.

module ibex_wrapper (
    // Clock and Reset
    input clk_i,
    input rst_ni,

    // Core configuration
    input [31:0] hart_id_i,
    input [31:0] boot_addr_i,

    // Instruction memory interface
    output logic        instr_req_o,
    input  logic        instr_gnt_i,
    input  logic        instr_rvalid_i,
    output logic [31:0] instr_addr_o,
    input  logic [31:0] instr_rdata_i,
    input  logic        instr_err_i,

    // Data memory interface
    output data_req_o,
    input data_gnt_i,
    input data_rvalid_i,
    output data_we_o,
    output [3:0] data_be_o,
    output [31:0] data_addr_o,
    output [31:0] data_wdata_o,
    input [31:0] data_rdata_i,
    input data_err_i
);

  // Based on ibex_simple_system.sv

  ibex_top_tracing #(
      .RV32E(0),
      .RV32M(ibex_pkg::RV32MFast),
      .RV32B(ibex_pkg::RV32BNone),
      .RegFile(ibex_pkg::RegFileFF),
      .BranchTargetALU(0),
      .WritebackStage(0),
      .ICache(0),
      .ICacheECC(0),
      .ICacheScramble(0),
      .BranchPredictor(0),
      .DbgTriggerEn(0),
      .SecureIbex(0),
      .PMPEnable(0),
      .PMPGranularity(0),
      .PMPNumRegions(4),
      .MHPMCounterNum(0),
      .MHPMCounterWidth(40)
  ) i_ibex (
      .clk_i,
      .rst_ni,
      .test_en_i  (1'b1),
      .ram_cfg_i  (prim_ram_1p_pkg::RAM_1P_CFG_DEFAULT),
      .hart_id_i  (32'b0),
      .boot_addr_i(32'h1000),

      .instr_req_o,
      .instr_gnt_i,
      .instr_rvalid_i,
      .instr_addr_o,
      .instr_rdata_i,
      .instr_rdata_intg_i(),
      .instr_err_i,

      .data_req_o,
      .data_gnt_i,
      .data_rvalid_i,
      .data_we_o,
      .data_be_o,
      .data_addr_o,
      .data_wdata_o,
      .data_wdata_intg_o(),
      .data_rdata_i,
      .data_rdata_intg_i(),
      .data_err_i,

      .irq_software_i(1'b0),
      .irq_timer_i   (1'b0),
      .irq_external_i(1'b0),
      .irq_fast_i    (15'b0),
      .irq_nm_i      (1'b0),

      .scramble_key_valid_i('0),
      .scramble_key_i      ('0),
      .scramble_nonce_i    ('0),
      .scramble_req_o      (),

      .debug_req_i        (1'b0),
      .crash_dump_o       (),
      .double_fault_seen_o(),

      .fetch_enable_i        (ibex_pkg::IbexMuBiOn),
      .alert_minor_o         (),
      .alert_major_internal_o(),
      .alert_major_bus_o     (),
      .core_sleep_o          (),
      .scan_rst_ni           (1'b1)

  );


endmodule
