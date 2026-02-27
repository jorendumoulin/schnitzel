package core

import chisel3._
import chisel3.util.HasBlackBoxPath
import java.nio.file.{Files, Paths}

class ibex_wrapper_flattened extends BlackBox with HasBlackBoxPath {

  val io = IO(new Bundle {

    // Clock and Reset
    val clk_i = Input(Clock())
    val rst_ni = Input(Bool())

    // Core configuration
    val hart_id_i = Input(UInt(32.W))
    val boot_addr_i = Input(UInt(32.W))

    // Instruction memory interface
    val instr_req_o = Output(Bool())
    val instr_gnt_i = Input(Bool())
    val instr_rvalid_i = Input(Bool())
    val instr_addr_o = Output(UInt(32.W))
    val instr_rdata_i = Input(UInt(32.W))
    val instr_err_i = Input(Bool())

    // Data memory interface
    val data_req_o = Output(Bool())
    val data_gnt_i = Input(Bool())
    val data_rvalid_i = Input(Bool())
    val data_we_o = Output(Bool())
    val data_be_o = Output(UInt(4.W))
    val data_addr_o = Output(UInt(32.W))
    val data_wdata_o = Output(UInt(32.W))
    val data_rdata_i = Input(UInt(32.W))
    val data_err_i = Input(Bool())

    // CSR interface
    val csr_ext_ready_i = Input(Bool())
    val csr_ext_valid_o = Output(Bool())
    val csr_ext_addr_o = Output(UInt(12.W))
    val csr_ext_wdata_o = Output(UInt(32.W))
    val csr_ext_op_o = Output(UInt(2.W))
    val csr_ext_rdata_i = Input(UInt(32.W))
  })

  // Add ibex resources:
  addPath("/home/joren/phd/schnitzel/src/main/resources/ibex/ibex_wrapper_flattened.sv")

}
