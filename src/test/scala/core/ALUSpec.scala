package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers
import core.Opcodes._

class ALUSpec extends AnyFreeSpec with Matchers with ChiselSim {
  "ALU should perform all operations correctly" in {
    simulate(new ALU) { dut =>
      // Test ADD and SUB
      dut.io.op.poke(ALU_ADD)
      dut.io.srcA.poke(10.U)
      dut.io.srcB.poke(32.U)
      dut.clock.step()
      dut.io.result.expect(42.U)

      dut.io.op.poke(ALU_SUB)
      dut.io.srcA.poke(100.U)
      dut.io.srcB.poke(58.U)
      dut.clock.step()
      dut.io.result.expect(42.U)
      dut.clock.step()

      // Test AND, OR, XOR
      dut.io.op.poke(ALU_AND)
      dut.io.srcA.poke("hFF00FF00FF00FF00".U)
      dut.io.srcB.poke("h00FF00FF00FF00FF".U)
      dut.clock.step()
      dut.io.result.expect(0.U)

      dut.io.op.poke(ALU_OR)
      dut.io.srcA.poke("hFF00FF00FF00FF00".U)
      dut.io.srcB.poke("h00FF00FF00FF00FF".U)
      dut.clock.step()
      dut.io.result.expect("hFFFFFFFFFFFFFFFF".U)

      dut.io.op.poke(ALU_XOR)
      dut.io.srcA.poke("hFF00FF00FF00FF00".U)
      dut.io.srcB.poke("h00FF00FF00FF00FF".U)
      dut.clock.step()
      dut.io.result.expect("hFFFFFFFFFFFFFFFF".U)
      dut.clock.step()

      // Test SLT and SLTU
      dut.io.op.poke(ALU_SLT)
      dut.io.srcA.poke((-5).S(64.W).asUInt)
      dut.io.srcB.poke(3.U)
      dut.clock.step()
      dut.io.result.expect(1.U)

      dut.io.op.poke(ALU_SLT)
      dut.io.srcA.poke(10.U)
      dut.io.srcB.poke(3.U)
      dut.clock.step()
      dut.io.result.expect(0.U)

      dut.io.op.poke(ALU_SLTU)
      dut.io.srcA.poke(2.U)
      dut.io.srcB.poke(3.U)
      dut.clock.step()
      dut.io.result.expect(1.U)

      dut.io.op.poke(ALU_SLTU)
      dut.io.srcA.poke("hFFFFFFFFFFFFFFFF".U)
      dut.io.srcB.poke(0.U)
      dut.clock.step()
      dut.io.result.expect(0.U)
      dut.clock.step()

      // Test SLL, SRL, SRA
      dut.io.op.poke(ALU_SLL)
      dut.io.srcA.poke(1.U)
      dut.io.srcB.poke(4.U)
      dut.clock.step()
      dut.io.result.expect(16.U)

      dut.io.op.poke(ALU_SRL)
      dut.io.srcA.poke("hF000000000000000".U)
      dut.io.srcB.poke(60.U)
      dut.clock.step()
      dut.io.result.expect(15.U)

      dut.io.op.poke(ALU_SRA)
      dut.io.srcA.poke((-16).S(64.W).asUInt)
      dut.io.srcB.poke(2.U)
      dut.clock.step()
      dut.io.result.expect((-4).S(64.W).asUInt)
      dut.clock.step()

      // Test MUL, MULH, MULHU, MULHSU
      dut.io.op.poke(ALU_MUL)
      dut.io.srcA.poke(7.U)
      dut.io.srcB.poke(6.U)
      dut.clock.step()
      dut.io.result.expect(42.U)

      dut.io.op.poke(ALU_MULH)
      dut.io.srcA.poke("hFFFFFFFFFFFFFFFF".U)
      dut.io.srcB.poke(2.U)
      dut.clock.step()
      // MULH: signed high bits, for -1 * 2 = -2, high bits are all ones
      dut.io.result.expect("hFFFFFFFFFFFFFFFF".U)

      dut.io.op.poke(ALU_MULHU)
      dut.io.srcA.poke("hFFFFFFFFFFFFFFFF".U)
      dut.io.srcB.poke(2.U)
      dut.clock.step()
      // MULHU: unsigned high bits, for max * 2, high bits are 1
      dut.io.result.expect(1.U)

      dut.io.op.poke(ALU_MULHSU)
      dut.io.srcA.poke((-1).S(64.W).asUInt)
      dut.io.srcB.poke(2.U)
      dut.clock.step()
      // MULHSU: signed * unsigned, high bits for -1 * 2
      dut.io.result.expect("hFFFFFFFFFFFFFFFF".U)
      dut.clock.step()

      // Test DIV, DIVU, REM, REMU
      dut.io.op.poke(ALU_DIV)
      dut.io.srcA.poke(42.U)
      dut.io.srcB.poke(7.U)
      dut.clock.step()
      dut.io.result.expect(6.U)

      dut.io.op.poke(ALU_DIVU)
      dut.io.srcA.poke(42.U)
      dut.io.srcB.poke(7.U)
      dut.clock.step()
      dut.io.result.expect(6.U)

      dut.io.op.poke(ALU_REM)
      dut.io.srcA.poke(42.U)
      dut.io.srcB.poke(7.U)
      dut.clock.step()
      dut.io.result.expect(0.U)

      dut.io.op.poke(ALU_REMU)
      dut.io.srcA.poke(43.U)
      dut.io.srcB.poke(7.U)
      dut.clock.step()
      dut.io.result.expect(1.U)
    }
  }
}
