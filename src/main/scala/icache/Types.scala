package icache

import chisel3._
import chisel3.util.log2Up

object ICacheConfig {
  // address bitwidth, 32-bit for RV32
  val addrWidth = 32
  // instruction bitwidth
  val instrWidth = 32
  // width of a cache line (matches AXI bus for now)
  val lineWidth = 512;
  // number of cache lines (64*512bit ~ 4kB cache size)
  val cacheLines = 64;
  // number of instructions per cache line
  val instrsPerLine = lineWidth / instrWidth;
  // bits for byte within instruction
  val byteBits = log2Up(instrWidth / 8);
  // bits to determine instruction within cache line
  val instrBits = log2Up(lineWidth / instrWidth);
  // bits to determine cache line
  val lineBits = log2Up(ICacheConfig.cacheLines)
  // bits required for tag
  val tagWidth = addrWidth - lineBits - instrBits - byteBits;
}

class IReq extends Bundle {
  val addr = UInt(ICacheConfig.addrWidth.W)
}

// 32 bit instructions
class IRsp extends Bundle {
  val data = UInt(ICacheConfig.instrWidth.W)
}

// Decomposition of request address
class ICacheRead extends Bundle {
  val tag = UInt(ICacheConfig.tagWidth.W)
  val line = UInt(ICacheConfig.lineBits.W)
  val instr = UInt(ICacheConfig.instrBits.W)
  val byte = UInt(ICacheConfig.byteBits.W)
}

// Interface to every bank in a cache line
class BankPort extends Bundle {
  val line = UInt(ICacheConfig.lineBits.W)
  val wdata = UInt(ICacheConfig.instrWidth.W)
  val resp = UInt(ICacheConfig.instrWidth.W)
  val enable = Bool()
  val write = Bool()
}

class ICacheRsp extends Bundle {
  // was a request made?
  val req = Wire(Bool())
  // is the cache line valid?
  val valid = Wire(Bool())
  // tag of the cache line
  val tag = Wire(UInt(ICacheConfig.tagWidth.W))
  // tag of the request
  val tag_target = Wire(UInt(ICacheConfig.tagWidth.W))
  // instr stored in cache
  val instr = Wire(UInt(ICacheConfig.instrWidth.W))
  def hit: Bool = req && valid && tag === tag_target;
  def miss: Bool = req && (~valid || tag =/= tag_target);
}
