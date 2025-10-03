package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers

class RegisterFileSpec extends AnyFreeSpec with Matchers with ChiselSim {
  "RegisterFile should read and write registers correctly" in {
    simulate(new RegisterFile) { rf =>
      // Write to x1
      rf.io.rdAddr.poke(1.U)
      rf.io.rdData.poke(0x123456789abcdef0L.U)
      rf.io.rdWrite.poke(true.B)
      rf.clock.step()

      // Write to x2
      rf.io.rdAddr.poke(2.U)
      rf.io.rdData.poke(0x0fedcba987654321L.U)
      rf.io.rdWrite.poke(true.B)
      rf.clock.step()

      // Read x1 and x2
      rf.io.rs1Addr.poke(1.U)
      rf.io.rs2Addr.poke(2.U)
      rf.io.rdWrite.poke(false.B)
      rf.clock.step()

      rf.io.rs1Data.expect(0x123456789abcdef0L.U)
      rf.io.rs2Data.expect(0x0fedcba987654321L.U)
    }
  }

  "RegisterFile should always read zero from x0 and never write to x0" in {
    simulate(new RegisterFile) { rf =>
      // Attempt to write to x0
      rf.io.rdAddr.poke(0.U)
      rf.io.rdData.poke(BigInt("FFFFFFFFFFFFFFFF", 16).U(64.W))
      rf.io.rdWrite.poke(true.B)
      rf.clock.step()

      // Read from x0
      rf.io.rs1Addr.poke(0.U)
      rf.io.rs2Addr.poke(0.U)
      rf.io.rdWrite.poke(false.B)
      rf.clock.step()

      rf.io.rs1Data.expect(0.U)
      rf.io.rs2Data.expect(0.U)
    }
  }

  "RegisterFile should not overwrite registers when rdWrite is false" in {
    simulate(new RegisterFile) { rf =>
      // Write to x3
      rf.io.rdAddr.poke(3.U)
      rf.io.rdData.poke(0xdeadbeefL.U)
      rf.io.rdWrite.poke(true.B)
      rf.clock.step()

      // Attempt to overwrite x3 with rdWrite = false
      rf.io.rdAddr.poke(3.U)
      rf.io.rdData.poke(0xcafebabeL.U)
      rf.io.rdWrite.poke(false.B)
      rf.clock.step()

      // Read from x3
      rf.io.rs1Addr.poke(3.U)
      rf.io.rs2Addr.poke(3.U)
      rf.clock.step()

      rf.io.rs1Data.expect(0xdeadbeefL.U)
      rf.io.rs2Data.expect(0xdeadbeefL.U)
    }
  }
}
