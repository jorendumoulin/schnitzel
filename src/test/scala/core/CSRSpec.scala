package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers

class CSRSpec extends AnyFreeSpec with Matchers with ChiselSim {
  "CSR should read and write mstatus CSR correctly" in {
    simulate(new CSR) { dut =>
      val addr = "h300".U(12.W) // mstatus
      val testValue = BigInt("DEADBEEFCAFEBABE", 16).U(64.W)

      // Write to mstatus
      dut.io.addr.poke(addr)
      dut.io.wdata.poke(testValue)
      dut.io.wen.poke(true.B)
      dut.io.ren.poke(false.B)
      dut.clock.step()

      // Read from mstatus
      dut.io.wen.poke(false.B)
      dut.io.ren.poke(true.B)
      dut.clock.step()
      dut.io.rdata.expect(testValue)
    }
  }

  "CSR should read and write mie CSR correctly" in {
    simulate(new CSR) { dut =>
      val addr = "h304".U(12.W) // mie
      val testValue = BigInt("123456789ABCDEF0", 16).U(64.W)

      // Write to mie
      dut.io.addr.poke(addr)
      dut.io.wdata.poke(testValue)
      dut.io.wen.poke(true.B)
      dut.io.ren.poke(false.B)
      dut.clock.step()

      // Read from mie
      dut.io.wen.poke(false.B)
      dut.io.ren.poke(true.B)
      dut.clock.step()
      dut.io.rdata.expect(testValue)
    }
  }

  "CSR should return zero for unsupported CSR addresses" in {
    simulate(new CSR) { dut =>
      val addr = "h999".U(12.W) // unsupported address

      dut.io.addr.poke(addr)
      dut.io.wen.poke(false.B)
      dut.io.ren.poke(true.B)
      dut.clock.step()
      dut.io.rdata.expect(0.U)
    }
  }

  "CSR should not write to CSR when wen is false" in {
    simulate(new CSR) { dut =>
      val addr = "h305".U(12.W) // mtvec
      val testValue = BigInt("FEEDFACECAFEBEEF", 16).U(64.W)

      // Try to write with wen = false
      dut.io.addr.poke(addr)
      dut.io.wdata.poke(testValue)
      dut.io.wen.poke(false.B)
      dut.io.ren.poke(false.B)
      dut.clock.step()

      // Read from mtvec (should still be zero)
      dut.io.wen.poke(false.B)
      dut.io.ren.poke(true.B)
      dut.clock.step()
      dut.io.rdata.expect(0.U)
    }
  }

  "CSR should update multiple CSRs independently" in {
    simulate(new CSR) { dut =>
      val addr_mstatus = "h300".U(12.W)
      val addr_mie = "h304".U(12.W)
      val val_mstatus = BigInt("1111111111111111", 16).U(64.W)
      val val_mie = BigInt("2222222222222222", 16).U(64.W)

      // Write to mstatus
      dut.io.addr.poke(addr_mstatus)
      dut.io.wdata.poke(val_mstatus)
      dut.io.wen.poke(true.B)
      dut.io.ren.poke(false.B)
      dut.clock.step()

      // Write to mie
      dut.io.addr.poke(addr_mie)
      dut.io.wdata.poke(val_mie)
      dut.io.wen.poke(true.B)
      dut.io.ren.poke(false.B)
      dut.clock.step()

      // Read from mstatus
      dut.io.addr.poke(addr_mstatus)
      dut.io.wen.poke(false.B)
      dut.io.ren.poke(true.B)
      dut.clock.step()
      dut.io.rdata.expect(val_mstatus)

      // Read from mie
      dut.io.addr.poke(addr_mie)
      dut.io.wen.poke(false.B)
      dut.io.ren.poke(true.B)
      dut.clock.step()
      dut.io.rdata.expect(val_mie)
    }
  }
}
