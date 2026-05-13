package memory

import chisel3._
import core.DecoupledBusIO
import chisel3.util.log2Ceil
import chisel3.simulator.PeekPokeAPI.TestableData

class MemWidthConverter(addrWidth: Int, dataWidthIn: Int, dataWidthOut: Int) extends Module {

  val io = IO(new Bundle {
    val in = Flipped(new DecoupledBusIO(addrWidth, dataWidthIn));
    val out = new DecoupledBusIO(addrWidth, dataWidthOut);
  })

  // By default, bulk connect everything and overwrite later
  io.in <> io.out

  // Calculate conversion ratios
  assert(dataWidthOut >= dataWidthIn, "only up-conversion is supported")
  assert(dataWidthOut % dataWidthIn == 0)
  val upConversion = dataWidthOut / dataWidthIn
  val upConversionBits = log2Ceil(upConversion)
  assert(math.pow(2, upConversionBits) == upConversion)

  // Send wdata to every part
  io.out.req.bits.wdata := VecInit(Seq.fill(upConversion)(io.in.req.bits.wdata)).asUInt

  // Align strobe with address
  val byteBits = log2Ceil(dataWidthIn / 8)
  val laneSel = io.in.req.bits.addr(upConversionBits + byteBits - 1, byteBits)
  io.out.req.bits.ben := (io.in.req.bits.ben.asUInt << (laneSel * (dataWidthIn / 8).U))

  // Take correct response based on previous request address
  val prevLaneSel = Reg(UInt(upConversionBits.W))
  when(io.in.req.fire) { prevLaneSel := laneSel }
  val outLanes = io.out.rsp.bits.data.asTypeOf(Vec(upConversion, io.in.rsp.bits.data.cloneType))
  io.in.rsp.bits.data := outLanes(prevLaneSel)

}
