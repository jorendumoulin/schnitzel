package core

import chisel3._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers

class ControlUnitSpec extends AnyFreeSpec with Matchers with ChiselSim {

  "ControlUnit should assert globalStall when stallFetch is true" in {
    simulate(new ControlUnit) { dut =>
      dut.io.stallFetch.poke(true.B)
      dut.io.stallMemory.poke(false.B)
      dut.clock.step()
      dut.io.globalStall.expect(true.B)
    }
  }

  "ControlUnit should assert globalStall when stallMemory is true" in {
    simulate(new ControlUnit) { dut =>
      dut.io.stallFetch.poke(false.B)
      dut.io.stallMemory.poke(true.B)
      dut.clock.step()
      dut.io.globalStall.expect(true.B)
    }
  }

  "ControlUnit should deassert globalStall when neither stallFetch nor stallMemory is true" in {
    simulate(new ControlUnit) { dut =>
      dut.io.stallFetch.poke(false.B)
      dut.io.stallMemory.poke(false.B)
      dut.clock.step()
      dut.io.globalStall.expect(false.B)
    }
  }

  "ControlUnit should assert globalStall when both stallFetch and stallMemory are true" in {
    simulate(new ControlUnit) { dut =>
      dut.io.stallFetch.poke(true.B)
      dut.io.stallMemory.poke(true.B)
      dut.clock.step()
      dut.io.globalStall.expect(true.B)
    }
  }
}
