package core

import chisel3._
import chisel3.util.HasBlackBoxResource
import chisel3.util.Fill
import chisel3.util.Counter

class Core(hartId: Int) extends Module {

  val io = IO(new Bundle {

    val imem =
      new DecoupledBusIO(
        CoreConfig.addrWidth,
        CoreConfig.instrWidth
      ) // Instruction memory interface

    val dmem =
      new DecoupledBusIO(
        CoreConfig.addrWidth,
        CoreConfig.dataWidth
      ) // Decoupled data memory interface
  })

  val ibex = Module(new ibex_wrapper())
  ibex.io.clk_i := clock
  ibex.io.rst_ni := ~reset.asBool

  ibex.io.hart_id_i := hartId.U
  ibex.io.boot_addr_i := 0x1000.U

  // Instruction memory interface
  io.imem.req.valid := ibex.io.instr_req_o
  io.imem.req.bits.addr := ibex.io.instr_addr_o
  io.imem.req.bits.wen := false.B
  io.imem.req.bits.ben := Fill(4, 1.U);
  io.imem.req.bits.wdata := 0.U
  io.imem.rsp.ready := true.B
  ibex.io.instr_gnt_i := io.imem.req.ready
  ibex.io.instr_rvalid_i := io.imem.rsp.valid
  ibex.io.instr_rdata_i := io.imem.rsp.bits.data
  ibex.io.instr_err_i := 0.U

  // Data memory interface
  io.dmem.req.valid := ibex.io.data_req_o
  io.dmem.req.bits.addr := ibex.io.data_addr_o
  io.dmem.req.bits.wen := ibex.io.data_we_o
  io.dmem.req.bits.ben := ibex.io.data_be_o
  io.dmem.req.bits.wdata := ibex.io.data_wdata_o
  ibex.io.data_gnt_i := io.dmem.req.ready
  io.dmem.rsp.ready := true.B
  ibex.io.data_rvalid_i := io.dmem.rsp.valid
  ibex.io.data_rdata_i := io.dmem.rsp.bits.data
  ibex.io.data_err_i := 0.U

  val (_, counterWrap) = Counter(ibex.io.csr_ext_valid_o, 4)

  // CSR interface
  ibex.io.csr_ext_ready_i := counterWrap
  ibex.io.csr_ext_rdata_i := 177.U

}
