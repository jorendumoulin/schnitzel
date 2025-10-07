package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import core.Opcodes._
import org.scalatest.matchers.must.Matchers

class CoreSpec extends AnyFreeSpec with Matchers with ChiselSim {

  "Core should fetch instructions" in {
    simulate(new Core) { dut =>
      // Simulate memory responses and verify requests
      for (_ <- 0 until 10) {
        // Simulate memory being ready and providing a response
        dut.io.imem.req.ready.poke(true.B)
        // Expect the core to issue a memory request
        dut.io.imem.req.valid.expect(true.B)
        dut.clock.step()
      }
    }
  }

  "Core should execute lw instruction" in {
    simulate(new Core) { dut =>
      // Issue LW instruction: lw x1, 12(x2)
      val lwInstr = "h00c12083".U(32.W)
      dut.io.imem.req.ready.poke(true.B)
      dut.io.imem.rsp.data.poke(lwInstr)

      // Expect the core to issue a memory read request
      dut.io.dmem.req.valid.expect(true.B)
      dut.io.dmem.req.bits.ren.expect(true.B)

    }
  }

  "Core should execute sw instruction" in {
    simulate(new Core) { dut =>
      // Issue a SW instruction: SW x1, 8(x2)
      val swInstr = "h00112423".U(32.W)
      dut.io.imem.req.ready.poke(true.B)
      dut.io.imem.rsp.data.poke(swInstr)

      // Expect the core to issue a memory write request
      dut.io.dmem.req.valid.expect(true.B)
      dut.io.dmem.req.bits.wen.expect(true.B)
      dut.io.dmem.req.bits.wdata.expect(0.U) // Assuming x1 was loaded with 0
    }
  }
}
