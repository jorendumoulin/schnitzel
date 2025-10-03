package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers

class CoreSpec extends AnyFreeSpec with Matchers with ChiselSim {
  "Core should execute a simple program and update registers and CSRs" in {
    simulate(new Core) { dut =>
      // Simple memory model for instruction and data
      val instrMem = Array.fill(256)(0.U(32.W))
      val dataMem = Array.fill(256)(0.U(64.W))

      // Example program:
      // 0x0000: LUI x1, 0x12345
      // 0x0004: ADDI x2, x1, 0x7
      // 0x0008: CSRRW x3, mstatus, x2
      // 0x000C: CSRRW x4, mstatus, x0
      instrMem(0) = "h12345037".U // LUI x1, 0x12345
      instrMem(1) = "h00708113".U // ADDI x2, x1, 7
      instrMem(2) = "h30219173".U // CSRRW x3, mstatus, x2
      instrMem(3) = "h302201f3".U // CSRRW x4, mstatus, x0

      // Helper to poke instruction memory
      def pokeInstrMem(addr: UInt): Unit = {
        val idx = (addr.litValue / 4).toInt
        if (idx < instrMem.length) {
          dut.io.imem.rdata.poke(instrMem(idx))
        } else {
          dut.io.imem.rdata.poke(0.U)
        }
      }

      // Helper to poke data memory (not used in this test)
      dut.io.dmem.req.ready.poke(true.B)
      dut.io.imem.req.ready.poke(true.B)
      dut.io.dmem.rdata.poke(0.U)
      dut.io.imem.rdata.poke(0.U)

      // Reset core
      dut.reset.poke(true.B)
      dut.clock.step()
      dut.reset.poke(false.B)
      dut.clock.step()

      // Step through instructions
      for (cycle <- 0 until 8) {
        pokeInstrMem(dut.pc.peek())
        dut.clock.step()
      }

      // Check register values
      val x1 = dut.regFile.regs(1).peek().litValue
      val x2 = dut.regFile.regs(2).peek().litValue
      val x3 = dut.regFile.regs(3).peek().litValue
      val x4 = dut.regFile.regs(4).peek().litValue

      // Check CSR mstatus value
      val mstatus = dut.csr.mstatus.peek().litValue

      // Assertions
      x1 mustBe 0x12345000L
      x2 mustBe (0x12345000L + 7)
      x3 mustBe 0L
      x4 mustBe (0x12345000L + 7)
      mstatus mustBe 0L
    }
  }
}
