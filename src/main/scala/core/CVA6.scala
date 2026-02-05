package core

import chisel3._
import chisel3.util.{HasBlackBoxResource, Decoupled}
import axi.AXIBundle
import axi.AXIConfig

import chisel3._
import circt.stage.ChiselStage

class cva6_wrapper_flattened extends BlackBox with HasBlackBoxResource {

  val io = IO(new Bundle {

    val clk_i = Input(Clock())
    val rst_ni = Input(Bool())
    val boot_addr_i = Input(UInt(64.W))
    val hart_id_i = Input(UInt(32.W))
    val axi = new AXIBundle(new AXIConfig);

  })

  // Add cva6 resources:
  addResource("/cva6/cva6_wrapper_flattened.sv")

}

class CVA6 extends Module {
  val io = IO(new Bundle { val axi = new AXIBundle(new AXIConfig) })
  val cva6 = Module(new cva6_wrapper_flattened)
  cva6.io.axi <> io.axi

  cva6.io.clk_i := clock
  cva6.io.rst_ni := ~reset.asBool
  cva6.io.boot_addr_i := 0x60000000L.U
  cva6.io.hart_id_i := 0.U
}
