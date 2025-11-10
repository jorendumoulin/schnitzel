package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import core.Opcodes._
import org.scalatest.matchers.must.Matchers

class CoreSpec extends AnyFreeSpec with Matchers with ChiselSim {

  "Core should handle all operations correctly" in {
    simulate(new Core) { dut =>
      // Test: Core should fetch instructions
      // Simulate memory responses and verify requests
      for (_ <- 0 until 10) {
        // Simulate memory being ready and providing a response
        dut.io.imem.req.ready.poke(true.B)
        // Expect the core to issue a memory request
        dut.io.imem.req.valid.expect(true.B)
        dut.clock.step()
      }
      dut.clock.step()

      // Test: Core should execute lw instruction
      // Issue LW instruction: lw x1, 12(x2)
      val lwInstr = "h00c12083".U(32.W)
      dut.io.imem.req.ready.poke(true.B)
      dut.io.imem.rsp.data.poke(lwInstr)

      // Expect the core to issue a memory read request
      dut.io.dmem.req.valid.expect(true.B)
      dut.io.dmem.req.bits.ren.expect(true.B)
      dut.clock.step()

      // Test: Core should execute sw instruction
      // Issue a SW instruction: SW x1, 8(x2)
      val swInstr = "h00112423".U(32.W)
      dut.io.imem.req.ready.poke(true.B)
      dut.io.imem.rsp.data.poke(swInstr)

      // Expect the core to issue a memory write request
      dut.io.dmem.req.valid.expect(true.B)
      dut.io.dmem.req.bits.wen.expect(true.B)
      dut.io.dmem.req.bits.wdata.expect(0.U) // Assuming x1 was loaded with 0
      dut.clock.step()

      // Test: Core should execute addi instruction
      // Issue ADDI instruction: addi x11, x11, 28
      val addiInstr = "h01c58593".U(32.W)
      dut.io.imem.req.ready.poke(true.B)
      dut.io.imem.rsp.data.poke(addiInstr)

      // For ADDI, no memory request should be made
      // The core should just proceed to the next instruction
      dut.clock.step()
    }
  }
}
