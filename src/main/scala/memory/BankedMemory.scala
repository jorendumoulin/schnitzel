package memory

import chisel3._
import chisel3.util.{MemoryReadWritePort, SRAM}

/** Helper for instantiating a bank of byte-masked SRAMs (one read/write port
  * per bank) suitable for use as cluster TCDM.
  */
object BankedMemory {

  /** Instantiate `numBanks` byte-masked SRAM banks, each `depth` words deep
    * and `dataWidth` bits wide, and return the per-bank read/write ports.
    */
  def apply(
      numBanks: Int,
      depth: Int,
      dataWidth: Int
  ): Vec[MemoryReadWritePort[Vec[UInt]]] = {
    val srams =
      VecInit(Seq.fill(numBanks)(SRAM.masked(depth, Vec(dataWidth / 8, UInt(8.W)), 0, 0, 1)))
    VecInit(srams.map(_.readwritePorts(0)))
  }
}
