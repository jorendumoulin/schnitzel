package memory

import chisel3._
import chisel3.util._

class Interconnect[T <: Data](
    numInp: Int,
    numOut: Int,
    reqType: T,
    rspType: T
) extends Module {

  val io = IO(new Bundle {
    val in_reqs = Vec(numInp, Decoupled(reqType.cloneType))
    val in_rsps = Vec(numInp, Flipped(Decoupled(rspType.cloneType)))
    val out_reqs = Vec(numOut, Decoupled(reqType.cloneType))
    val out_rsps = Vec(numOut, Flipped(Decoupled(rspType.cloneType)))
  })

}
