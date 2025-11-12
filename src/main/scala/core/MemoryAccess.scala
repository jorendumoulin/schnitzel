package core

import chisel3._
import chisel3.util._

/** MemoryAccess module Handles the data memory interface for load and store
  * operations.
  */
class MemoryAccess extends Module {
  val io = IO(new Bundle {
    val dmem =
      new BusIO(
        CoreConfig.addrWidth,
        CoreConfig.dataWidth
      ) // Data memory interface
    val memEn = Input(Bool()) // Memory enable signal
    val memWe = Input(Bool()) // Memory write enable signal
    val addr = Input(UInt(CoreConfig.addrWidth.W)) // Memory address
    val wdata = Input(UInt(CoreConfig.dataWidth.W)) // Data to write
    val rdata = Output(UInt(CoreConfig.dataWidth.W)) // Data read from memory
    val stall = Output(Bool()) // Stall signal for memory latency
  })

  // Issue memory request
  io.dmem.req.valid := io.memEn
  io.dmem.req.bits.addr := io.addr
  io.dmem.req.bits.wdata := io.wdata
  io.dmem.req.bits.wen := io.memWe

  // Read result from memory
  io.rdata := io.dmem.rsp.data

  // Stall signal for memory latency
  io.stall := io.memEn && !io.dmem.req.ready
}
