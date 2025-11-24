package memory

import chisel3._
import chisel3.util._
import core.BusReq

class MemoryIsland(
    numInp: Int,
    numBanks: Int,
    bankDepth: Int,
    dataWidth: Int
) extends Module {

  // Determine all bitwidths
  val addrWidth = log2Up(dataWidth);
  // 3 bits byte offset
  val byteOffset = log2Up(8);
  // bank selection offset, requires numBanks to be 2**n
  val bankSelWidth = log2Up(numBanks);
  val bankAddrWidth = addrWidth - bankSelWidth - addrWidth;

  val reqType = new BusReq(dataWidth, addrWidth)
  val rspType = new BusReq(dataWidth, addrWidth)

  val io = IO(new Bundle {
    val reqs = Vec(numInp, Decoupled(reqType.cloneType))
    val rsps = Vec(numInp, Flipped(Decoupled(rspType.cloneType)))
  })

  // The interconnect
  val interconnect = Module(new Interconnect(numInp, numBanks, reqType, rspType))
  interconnect.io.in_reqs <> io.reqs
  interconnect.io.in_rsps <> io.rsps

  // The memory banks (byte addressable)
  val mem = Seq.fill(numBanks)(SyncReadMem(bankDepth, Vec(8, UInt((dataWidth / 8).W))))

  for (bank <- 0 until numBanks) {
    interconnect.io.out_rsps(bank).bits
    val req = interconnect.io.out_reqs(bank);

  }

}
