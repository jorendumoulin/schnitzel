package top

import chisel3._
import axi.AXIConfig
import axi.AXIBundle
import csr.CsrIO
import axi.AxiToMem

class GlobalBarrier(axiConfig: AXIConfig) extends Module {

  val io = IO(new Bundle {
    val axi = Flipped(new AXIBundle(axiConfig));
    val csr = Flipped(new CsrIO);
  })

  // Convert axi to a regular memory request
  val axiToMem = Module(
    new AxiToMem(addrWidth = axiConfig.addrWidth, dataWidth = axiConfig.dataWidth, axiConfig = axiConfig)
  )
  axiToMem.io.axi <> io.axi

  // Default to no activity on the axi:
  axiToMem.io.mem := DontCare
  axiToMem.io.mem.req.ready := false.B
  axiToMem.io.mem.rsp.valid := false.B

  // Manager sends a valid request on a write to 0x300.U:
  val managerValid = RegInit(false.B)
  val managerRespPending = RegInit(false.B)
  axiToMem.io.mem.req.ready := ~managerRespPending
  when(axiToMem.io.mem.req.fire && axiToMem.io.mem.req.bits.wen && axiToMem.io.mem.req.bits.addr === 0x3000.U) {
    managerValid := true.B; managerRespPending := true.B
  }

  // Cluster sends a valid request on a read to 0x0
  val clusterValid = io.csr.req.valid && io.csr.req.bits.addr === 0x0.U

  // Synchronization happens when both cluster and manager send valid request
  val sync = managerValid && clusterValid
  when(sync) { managerValid := false.B }

  // Response to manager via axi:
  axiToMem.io.mem.rsp.bits := DontCare
  axiToMem.io.mem.rsp.valid := managerRespPending
  when(axiToMem.io.mem.rsp.fire) { managerRespPending := false.B }

  // Response to cluster via csr itf:
  io.csr.req.ready := sync
  io.csr.rsp.rdata := DontCare
}
