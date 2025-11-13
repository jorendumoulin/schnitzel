package core

import chisel3._
import chisel3.util.HasBlackBoxResource
import java.nio.file.{Files, Paths}

class ibex_wrapper extends BlackBox with HasBlackBoxResource {

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
  })

  // Add ibex resources:
  addResource("/ibex/IbexWrapperFlattened.sv")

}
