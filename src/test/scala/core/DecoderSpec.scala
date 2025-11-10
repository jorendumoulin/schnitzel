package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers

class DecoderSpec extends AnyFreeSpec with Matchers with ChiselSim {
  "Decoder should decode all instructions correctly" in {
    simulate(new Decoder) { d =>
      // Test LUI instruction
      val luiInstr = "h123450b7".U(32.W)
      d.io.instr.poke(luiInstr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x37
      d.io.rd.peek().litValue mustBe 1
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_COPY_B.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // Check that immediate is properly extracted (0x12345 << 12 = 0x12345000)
      d.io.immValue.peek().litValue mustBe 0x12345000L
      d.io.csrEn.peek().litToBoolean mustBe false
      d.clock.step()

      // Test ADDI instruction
      val addiInstr = "h00708113".U(32.W)
      d.io.instr.poke(addiInstr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x13
      d.io.rd.peek().litValue mustBe 2
      d.io.rs1.peek().litValue mustBe 1
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // Check immediate value extraction (0x007 = 7)
      d.io.immValue.peek().litValue mustBe 7
      // d.io.memEn.peek().litToBoolean mustBe false
      d.io.csrEn.peek().litToBoolean mustBe false
      d.clock.step()

      // Test ADDI with positive immediate (addi x11, x11, 28)
      val addiInstr28 = "h01c58593".U(32.W) // addi x11, x11, 28
      d.io.instr.poke(addiInstr28)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x13
      d.io.rd.peek().litValue mustBe 11
      d.io.rs1.peek().litValue mustBe 11
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // Check immediate value extraction (0x01c = 28)
      d.io.immValue.peek().litValue mustBe 28
      d.io.csrEn.peek().litToBoolean mustBe false
      d.clock.step()

      // Test ADDI with negative immediate
      val addiInstrNeg = "hffc58593".U(32.W) // addi x11, x11, -4
      d.io.instr.poke(addiInstrNeg)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x13
      d.io.rd.peek().litValue mustBe 11
      d.io.rs1.peek().litValue mustBe 11
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // Check immediate value extraction (0xffc = -4 when sign-extended)
      d.io.immValue.peek().litValue mustBe 4294967292L // 0xfffffffc as unsigned
      d.io.csrEn.peek().litToBoolean mustBe false
      d.clock.step()

      // Test AND instruction
      val andInstr = "h0020f233".U(32.W)
      d.io.instr.poke(andInstr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x33
      d.io.rd.peek().litValue mustBe 4
      d.io.rs1.peek().litValue mustBe 1
      d.io.rs2.peek().litValue mustBe 2
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_AND.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      d.io.csrEn.peek().litToBoolean mustBe false
      d.clock.step()

      // Test LW instruction
      val lwInstr = "h00822283".U(32.W)
      d.io.instr.poke(lwInstr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x03
      d.io.rd.peek().litValue mustBe 5
      d.io.rs1.peek().litValue mustBe 4
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      d.io.csrEn.peek().litToBoolean mustBe false
      d.clock.step()

      // Test SW instruction
      val swInstr = "h0051a323".U(32.W)
      d.io.instr.poke(swInstr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x23
      d.io.rs1.peek().litValue mustBe 3
      d.io.rs2.peek().litValue mustBe 5
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe false
      d.io.csrEn.peek().litToBoolean mustBe false
      d.clock.step()

      // Test CSRRW instruction
      val csrrwInstr = "h30039373".U(32.W)
      d.io.instr.poke(csrrwInstr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x73
      d.io.rd.peek().litValue mustBe 6
      d.io.rs1.peek().litValue mustBe 7
      d.io.csrEn.peek().litToBoolean mustBe true
      d.io.rdEn.peek().litToBoolean mustBe true
      d.clock.step()

      // Test AUIPC instruction
      val auipcInstr = "h12345097".U(32.W)
      d.io.instr.poke(auipcInstr)
      d.clock.step()
      d.io.opcode.peek().litValue mustBe 0x17
      d.io.rd.peek().litValue mustBe 1
      d.io.aluOp.peek().litValue mustBe core.Opcodes.ALU_ADD.litValue
      d.io.rdEn.peek().litToBoolean mustBe true
      // Check that immediate is properly extracted (0x12345 << 12 = 0x12345000)
      d.io.immValue.peek().litValue mustBe 0x12345000L
      d.io.csrEn.peek().litToBoolean mustBe false
    }
  }
}
