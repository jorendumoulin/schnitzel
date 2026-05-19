package cluster

import chisel3._

import core.{Core, CoreConfig, DecoupledBusIO}
import csr.{CsrDemux, CsrIO}
import memory.{MemDemux, MemWidthConverter}
import axi.{AXIBundle, AXIConfig, DecoupledIOToAXI}

/** A Core wrapped with its standard peripherals: an address-split MemDemux
  * (local TCDM vs external AXI), a width converter on the TCDM side, an AXI
  * adapter on the external side, and a CsrDemux that routes the global-sync
  * (0x800) and local-sync (0x810) ranges to dedicated ports and forwards the
  * rest to a single accelerator's CSR port.
  *
  * Built via [[CoreSubsystem.apply]]; the helper exposes the subsystem's
  * cluster-facing ports for the caller to attach to the icache, interconnect,
  * AXI mux, CSR combiner, and HW barrier.
  */
class CoreSubsystem private (
    val core: Core,
    private val memWidthConverter: MemWidthConverter,
    private val memToAxi: DecoupledIOToAXI,
    private val csrDemux: CsrDemux
) {
  def imem: DecoupledBusIO = core.io.imem
  def tcdm: DecoupledBusIO = memWidthConverter.io.out
  def axi: AXIBundle = memToAxi.io.axi
  def globalCsr: CsrIO = csrDemux.io.outs(0)
  def localCsr: CsrIO = csrDemux.io.outs(1)
}

object CoreSubsystem {

  /** Build a [[CoreSubsystem]].
    *
    * @param hartId         Hart ID for the underlying [[Core]].
    * @param accelerator    CSR slave port of an accelerator; receives every
    *                       CSR access that doesn't fall in the global- or
    *                       local-sync ranges.
    * @param axiId          AXI master ID used by this core's mem-to-axi
    *                       adapter.
    * @param tcdmDataWidth  Data width of the cluster TCDM.
    * @param wideAxiCfg     AXI config for the external (slave-facing) side.
    * @param splitThreshold Address at/above which dmem requests are routed
    *                       to AXI instead of TCDM.
    */
  def apply(
      hartId: Int,
      accelerator: CsrIO,
      axiId: Int,
      tcdmDataWidth: Int,
      wideAxiCfg: AXIConfig,
      splitThreshold: Int = 0x10000000
  ): CoreSubsystem = {
    val core = Module(new Core(hartId))

    val memMux = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, splitThreshold))
    memMux.io.in <> core.io.dmem

    val memWidthConverter =
      Module(new MemWidthConverter(CoreConfig.addrWidth, CoreConfig.dataWidth, tcdmDataWidth))
    memWidthConverter.io.in <> memMux.io.outs(1)

    val memToAxi = Module(
      new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, wideAxiCfg, axiId)
    )
    memMux.io.outs(0) <> memToAxi.io.bus

    val csrDemux = Module(new CsrDemux(3, Seq((0x800L, 0x10L), (0x810L, 0x10L))))
    csrDemux.io.in <> core.io.csr
    csrDemux.io.outs(2) <> accelerator

    new CoreSubsystem(core, memWidthConverter, memToAxi, csrDemux)
  }
}
