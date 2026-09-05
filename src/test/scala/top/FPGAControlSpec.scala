package top

import chisel3._
import chisel3.simulator.EphemeralSimulator._
import org.scalatest.flatspec.AnyFlatSpec
import csr.CsrOp

class FPGAControlSpec extends AnyFlatSpec {
  "FPGAControl" should "handle independent AXI channels, barriers, errors, and reset" in {
    simulate(new FPGAControl) { dut =>
      val axi = dut.io.axi
      axi.aw.valid.poke(false)
      axi.aw.bits.addr.poke(0)
      axi.aw.bits.prot.poke(0)
      axi.w.valid.poke(false)
      axi.w.bits.data.poke(0)
      axi.w.bits.strb.poke(0)
      axi.b.ready.poke(false)
      axi.ar.valid.poke(false)
      axi.ar.bits.addr.poke(0)
      axi.ar.bits.prot.poke(0)
      axi.r.ready.poke(false)
      dut.io.csr.req.valid.poke(false)
      dut.io.csr.req.bits.addr.poke(0)
      dut.io.csr.req.bits.wdata.poke(0)
      dut.io.csr.req.bits.op.poke(CsrOp.READ)
      dut.io.axiError.poke(false)
      dut.reset.poke(true)
      dut.clock.step(2)
      dut.reset.poke(false)
      dut.io.run.expect(false)

      def address(addr: Int): Unit = {
        axi.aw.ready.expect(true)
        axi.aw.bits.addr.poke(addr)
        axi.aw.valid.poke(true)
        dut.clock.step()
        axi.aw.valid.poke(false)
      }
      def data(value: Int, strb: Int): Unit = {
        axi.w.ready.expect(true)
        axi.w.bits.data.poke(value)
        axi.w.bits.strb.poke(strb)
        axi.w.valid.poke(true)
        dut.clock.step()
        axi.w.valid.poke(false)
      }
      def write(addr: Int, value: Int, strb: Int = 1, order: Int = 0, resp: Int = 0): Unit = {
        order match {
          case 0 => address(addr); dut.clock.step(3); data(value, strb)
          case 1 => data(value, strb); dut.clock.step(3); address(addr)
          case _ =>
            axi.aw.ready.expect(true)
            axi.w.ready.expect(true)
            axi.aw.bits.addr.poke(addr)
            axi.aw.valid.poke(true)
            axi.w.bits.data.poke(value)
            axi.w.bits.strb.poke(strb)
            axi.w.valid.poke(true)
            dut.clock.step()
            axi.aw.valid.poke(false)
            axi.w.valid.poke(false)
        }
        dut.clock.step()
        for (_ <- 0 until 3) {
          axi.b.valid.expect(true)
          axi.b.bits.expect(resp)
          axi.aw.ready.expect(false)
          axi.w.ready.expect(false)
          dut.clock.step()
        }
        axi.b.ready.poke(true)
        dut.clock.step()
        axi.b.ready.poke(false)
      }
      def read(addr: Int, value: Int, resp: Int = 0): Unit = {
        axi.ar.ready.expect(true)
        axi.ar.bits.addr.poke(addr)
        axi.ar.valid.poke(true)
        dut.clock.step()
        axi.ar.valid.poke(false)
        axi.ar.bits.addr.poke(0xfff)
        for (_ <- 0 until 3) {
          axi.r.valid.expect(true)
          axi.r.bits.data.expect(value)
          axi.r.bits.resp.expect(resp)
          axi.ar.ready.expect(false)
          dut.clock.step()
        }
        axi.r.ready.poke(true)
        dut.clock.step()
        axi.r.ready.poke(false)
      }

      read(0, 0)
      write(8, 1, resp = 2) // Cannot release a stopped cluster.
      write(0, 1, strb = 0, order = 1)
      read(0, 0)
      write(0, 1, order = 2)
      dut.io.run.expect(true)
      write(8, 1, order = 1)
      write(8, 1) // Releases coalesce before arrival.
      read(4, 5)
      dut.io.csr.req.valid.poke(true)
      dut.io.csr.req.bits.addr.poke(1)
      dut.io.csr.req.ready.expect(false)
      dut.clock.step(2)
      dut.io.csr.req.bits.addr.poke(0)
      dut.io.csr.req.ready.expect(true)
      dut.clock.step()
      dut.io.csr.req.valid.poke(false)
      dut.io.csr.req.ready.expect(false)
      read(12, 1)
      read(8, 0)
      dut.io.csr.req.valid.poke(true)
      read(4, 3)
      write(8, 1, order = 2)
      dut.io.csr.req.valid.poke(false)
      read(12, 2)
      dut.io.axiError.poke(true)
      dut.clock.step()
      dut.io.axiError.poke(false)
      read(16, 1)
      write(16, 1, strb = 0)
      read(16, 1)
      write(16, 1, order = 1)
      read(16, 0)
      dut.io.axiError.poke(true)
      write(16, 1, order = 2) // New error wins over clear.
      dut.io.axiError.poke(false)
      read(16, 1)
      write(4, 1, resp = 2)
      write(1, 1, order = 1, resp = 2)
      read(1, 0, resp = 2)
      read(20, 0, resp = 2)
      write(8, 1)
      write(0, 0, order = 1)
      dut.io.run.expect(false)
      read(4, 0)
      read(12, 0)
      read(16, 1) // RUN changes do not clear the diagnostic.
      address(0) // Reset discards an incomplete write.
      dut.reset.poke(true)
      dut.clock.step(2)
      dut.reset.poke(false)
      read(0, 0)
      read(16, 0)
      axi.b.valid.expect(false)
      axi.aw.ready.expect(true)
      axi.w.ready.expect(true)
    }
  }
}
