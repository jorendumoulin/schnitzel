package core

import chisel3._
import chisel3.util._

/** ControlUnit module Manages stalls and overall pipeline control. Coordinates
  * the flow of data between pipeline stages.
  */
class ControlUnit extends Module {
  val io = IO(new Bundle {
    val stallFetch = Input(Bool()) // Stall signal from fetch stage
    val stallMemory = Input(Bool()) // Stall signal from memory stage
    val globalStall = Output(Bool()) // Global stall signal for the pipeline
  })

  // Global stall signal is asserted if any stage requests a stall
  io.globalStall := io.stallFetch || io.stallMemory
}
