package core

import chisel3._
import chisel3.util.HasBlackBoxResource
import java.nio.file.{Files, Paths}

class ibex_top_tracing
    extends BlackBox(
      Map(
        "RV32E" -> 0,
        "RV32M" -> "ibex_pkg::RV32MFast",
        "RV32B" -> "ibex_pkg::RV32BNone",
        "RegFile" -> "ibex_pkg::RegFileFF",
        "BranchTargetALU" -> 0,
        "WritebackStage" -> 0,
        "ICache" -> 0,
        "ICacheECC" -> 0,
        "ICacheScramble" -> 0,
        "BranchPredictor" -> 0,
        "DbgTriggerEn" -> 0,
        "SecureIbex" -> 0,
        "PMPEnable" -> 0,
        "PMPGranularity" -> 0,
        "PMPNumRegions" -> 0,
        "MHPMCounterNum" -> 0,
        "MHPMCounterWidth" -> 40
      )
    )
    with HasBlackBoxResource {

  val io = IO(new Bundle {
    // Clock and reset
    val clk_i = Input(Clock())
    val rst_ni = Input(Bool())
    val test_en_i = Input(Bool()) // enable all clock gates for testing
    val scan_rst_ni = Input(Bool())
    val ram_cfg_i = Input(Bool())

    // Hart and boot configuration
    val hart_id_i = Input(UInt(32.W))
    val boot_addr_i = Input(UInt(32.W))

    // Instruction memory interface
    val instr_req_o = Output(Bool())
    val instr_gnt_i = Input(Bool())
    val instr_rvalid_i = Input(Bool())
    val instr_addr_o = Output(UInt(32.W))
    val instr_rdata_i = Input(UInt(32.W))
    val instr_rdata_intg_i = Input(UInt(7.W))
    val instr_err_i = Input(Bool())

    // Data memory interface
    val data_req_o = Output(Bool())
    val data_gnt_i = Input(Bool())
    val data_rvalid_i = Input(Bool())
    val data_we_o = Output(Bool())
    val data_be_o = Output(UInt(4.W))
    val data_addr_o = Output(UInt(32.W))
    val data_wdata_o = Output(UInt(32.W))
    val data_wdata_intg_o = Output(UInt(7.W))
    val data_rdata_i = Input(UInt(32.W))
    val data_rdata_intg_i = Input(UInt(7.W))
    val data_err_i = Input(Bool())

    // Interrupt inputs
    val irq_software_i = Input(Bool())
    val irq_timer_i = Input(Bool())
    val irq_external_i = Input(Bool())
    val irq_fast_i = Input(UInt(15.W))
    val irq_nm_i = Input(Bool()) // non-maskable interrupt

    // Scrambling Interface
    val scramble_key_valid_i = Input(Bool())
    val scramble_key_i = Input(Bool())
    val scramble_nonce_i = Input(Bool())
    val scramble_req_o = Output(Bool())

    // Debug Interface
    val debug_req_i = Input(Bool())
    val crash_dump_o = Output(Bool())
    val double_fault_seen_o = Output(Bool())

    // CPU Control Signals
    val fetch_enable_i = Input(Bool())
    val alert_minor_o = Output(Bool())
    val alert_major_internal_o = Output(Bool())
    val alert_major_bus_o = Output(Bool())
    val core_sleep_o = Output(Bool())
  })

  // Add ibex resources:

  val resources = Paths.get(getClass.getClassLoader.getResource(".").toURI())

  Files.list(resources.resolve("ibex-rtl")).forEach { p =>
    println(s"Adding Ibex resource: ${resources.relativize(p).toString()}")
    addResource(resources.relativize(p).toString())
  }

  Files.list(resources.resolve("ibex-ip")).forEach { p =>
    println(s"Adding Ibex resource: ${resources.relativize(p).toString()}")
    addResource(resources.relativize(p).toString())
  }

}
