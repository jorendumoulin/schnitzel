package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers

class DecoderSpec extends AnyFreeSpec with Matchers with ChiselSim {
  "Decoder should decode LUI instruction" in {
    simulate(new Decoder) { d =>
      val instr = "h123450b7".U(32.W)
      d.io.instr.poke(instr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x37
      d.io.rd.peek().litValue mustBe 1
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_COPY_B.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // d.io.memEn.peek().litToBoolean mustBe false
      d.io.csrEn.peek().litToBoolean mustBe false
    }
  }

  "Decoder should decode ADDI instruction" in {
    simulate(new Decoder) { d =>
      val instr = "h00708113".U(32.W)
      d.io.instr.poke(instr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x13
      d.io.rd.peek().litValue mustBe 2
      d.io.rs1.peek().litValue mustBe 1
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // d.io.memEn.peek().litToBoolean mustBe false
      d.io.csrEn.peek().litToBoolean mustBe false
    }
  }

  "Decoder should decode AND instruction" in {
    simulate(new Decoder) { d =>
      val instr = "h0020f233".U(32.W)
      d.io.instr.poke(instr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x33
      d.io.rd.peek().litValue mustBe 4
      d.io.rs1.peek().litValue mustBe 1
      d.io.rs2.peek().litValue mustBe 2
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_AND.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // d.io.memEn.peek().litToBoolean mustBe false
      d.io.csrEn.peek().litToBoolean mustBe false
    }
  }

  "Decoder should decode LW instruction" in {
    simulate(new Decoder) { d =>
      val instr = "h00822283".U(32.W)
      d.io.instr.poke(instr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x03
      d.io.rd.peek().litValue mustBe 5
      d.io.rs1.peek().litValue mustBe 4
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // d.io.memEn.peek().litToBoolean mustBe true
      d.io.csrEn.peek().litToBoolean mustBe false
    }
  }

  "Decoder should decode SW instruction" in {
    simulate(new Decoder) { d =>
      val instr = "h0051a323".U(32.W)
      d.io.instr.poke(instr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x23
      d.io.rs1.peek().litValue mustBe 3
      d.io.rs2.peek().litValue mustBe 5
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe false
      // d.io.memEn.peek().litToBoolean mustBe true
      // d.io.memWe.peek().litToBoolean mustBe true
      d.io.csrEn.peek().litToBoolean mustBe false
    }
  }

  "Decoder should decode CSRRW instruction" in {
    simulate(new Decoder) { d =>
      val instr = "h30039373".U(32.W)
      d.io.instr.poke(instr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x73
      d.io.rd.peek().litValue mustBe 6
      d.io.rs1.peek().litValue mustBe 7
      d.io.csrEn.peek().litToBoolean mustBe true
      // d.io.csrOp.peek().litValue mustBe core.Opcodes.CSR_RW.litValue
      // d.io.csrAddr.peek().litValue mustBe 0x300
      d.io.rdEn.peek().litToBoolean mustBe true
    }
  }
}
