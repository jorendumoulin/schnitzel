import chisel3._
import chisel3.util._

// /** Configuration holder for AXI widths. */
// case class AXIConfig(
//     idWidth: Int = 4,
//     addrWidth: Int = 32,
//     dataWidth: Int = 64,
//     strbWidth: Int = 8,
//     userWidth: Int = 1,
//     // widths for AXI pkg fields (customizable)
//     lenWidth: Int = 8, // usually 8 bits for AXI4 len
//     sizeWidth: Int = 3,
//     burstWidth: Int = 2,
//     cacheWidth: Int = 4,
//     protWidth: Int = 3,
//     qosWidth: Int = 4,
//     regionWidth: Int = 4,
//     atopWidth: Int = 2, // ATOP extension width (example)
//     respWidth: Int = 2 // AXI response (OKAY, EXOKAY, SLVERR, DECERR)
// )

// object AXIConfig {

//   /** Common default config (tweak widths to your platform) */
//   val default: AXIConfig = AXIConfig()
// }

// ///////////////////////////////////////////////////////////////////////////////
// // Low-level "axi_pkg" fields as simple UInts. If you have richer enums,
// // replace these with Chisel enums or chisel3.experimental.Enum as desired.
// ///////////////////////////////////////////////////////////////////////////////
// class AxiPkgFields(cfg: AXIConfig) {
//   def len_t = UInt(cfg.lenWidth.W)
//   def size_t = UInt(cfg.sizeWidth.W)
//   def burst_t = UInt(cfg.burstWidth.W)
//   def cache_t = UInt(cfg.cacheWidth.W)
//   def prot_t = UInt(cfg.protWidth.W)
//   def qos_t = UInt(cfg.qosWidth.W)
//   def region_t = UInt(cfg.regionWidth.W)
//   def atop_t = UInt(cfg.atopWidth.W)
//   def resp_t = UInt(cfg.respWidth.W)
// }

// ///////////////////////////////////////////////////////////////////////////////
// // AXI4+ATOP Channel Bundles (AW, W, B, AR, R)
// ///////////////////////////////////////////////////////////////////////////////
// class AWChan(cfg: AXIConfig) extends Bundle {
//   val id = UInt(cfg.idWidth.W)
//   val addr = UInt(cfg.addrWidth.W)
//   val len = UInt(cfg.lenWidth.W)
//   val size = UInt(cfg.sizeWidth.W)
//   val burst = UInt(cfg.burstWidth.W)
//   val lock = Bool()
//   val cache = UInt(cfg.cacheWidth.W)
//   val prot = UInt(cfg.protWidth.W)
//   val qos = UInt(cfg.qosWidth.W)
//   val region = UInt(cfg.regionWidth.W)
//   val atop = UInt(cfg.atopWidth.W)
//   val user = UInt(cfg.userWidth.W)

//   override def cloneType: this.type = new AWChan(cfg).asInstanceOf[this.type]
// }

// class WChan(cfg: AXIConfig) extends Bundle {
//   val data = UInt(cfg.dataWidth.W)
//   val strb = UInt(cfg.strbWidth.W)
//   val last = Bool()
//   val user = UInt(cfg.userWidth.W)

//   override def cloneType: this.type = new WChan(cfg).asInstanceOf[this.type]
// }

// class BChan(cfg: AXIConfig) extends Bundle {
//   val id = UInt(cfg.idWidth.W)
//   val resp = UInt(cfg.respWidth.W)
//   val user = UInt(cfg.userWidth.W)

//   override def cloneType: this.type = new BChan(cfg).asInstanceOf[this.type]
// }

// class ARChan(cfg: AXIConfig) extends Bundle {
//   val id = UInt(cfg.idWidth.W)
//   val addr = UInt(cfg.addrWidth.W)
//   val len = UInt(cfg.lenWidth.W)
//   val size = UInt(cfg.sizeWidth.W)
//   val burst = UInt(cfg.burstWidth.W)
//   val lock = Bool()
//   val cache = UInt(cfg.cacheWidth.W)
//   val prot = UInt(cfg.protWidth.W)
//   val qos = UInt(cfg.qosWidth.W)
//   val region = UInt(cfg.regionWidth.W)
//   val user = UInt(cfg.userWidth.W)

//   override def cloneType: this.type = new ARChan(cfg).asInstanceOf[this.type]
// }

// class RChan(cfg: AXIConfig) extends Bundle {
//   val id = UInt(cfg.idWidth.W)
//   val data = UInt(cfg.dataWidth.W)
//   val resp = UInt(cfg.respWidth.W)
//   val last = Bool()
//   val user = UInt(cfg.userWidth.W)

//   override def cloneType: this.type = new RChan(cfg).asInstanceOf[this.type]
// }

// ///////////////////////////////////////////////////////////////////////////////
// // Combined Request and Response Bundles
// // These mirror your req_t and resp_t SV structs but in a *Bundle form* for Chisel.
// // The request bundle groups the outbound channels and the handshake-valid/ready signals.
// ///////////////////////////////////////////////////////////////////////////////
// /** Request side: master -> slave signals (aw, w, ar + control flags) */
// class AXIReqBundle(cfg: AXIConfig) extends Bundle {
//   val aw = new AWChan(cfg)
//   val aw_valid = Bool()
//   val w = new WChan(cfg)
//   val w_valid = Bool()
//   val b_ready = Bool()
//   val ar = new ARChan(cfg)
//   val ar_valid = Bool()
//   val r_ready = Bool()

//   override def cloneType: this.type =
//     new AXIReqBundle(cfg).asInstanceOf[this.type]
// }

// /** Response side: slave -> master signals (aw_ready, ar_ready, w_ready,
//   * b_valid/b, r_valid/r)
//   */
// class AXIRespBundle(cfg: AXIConfig) extends Bundle {
//   val aw_ready = Bool()
//   val ar_ready = Bool()
//   val w_ready = Bool()
//   val b_valid = Bool()
//   val b = new BChan(cfg)
//   val r_valid = Bool()
//   val r = new RChan(cfg)

//   override def cloneType: this.type =
//     new AXIRespBundle(cfg).asInstanceOf[this.type]
// }

// ///////////////////////////////////////////////////////////////////////////////
// // AXI4-Lite Bundles
// ///////////////////////////////////////////////////////////////////////////////
// class AWChanLite(cfg: AXIConfig) extends Bundle {
//   val addr = UInt(cfg.addrWidth.W)
//   val prot = UInt(cfg.protWidth.W)
//   override def cloneType: this.type =
//     new AWChanLite(cfg).asInstanceOf[this.type]
// }

// class WChanLite(cfg: AXIConfig) extends Bundle {
//   val data = UInt(cfg.dataWidth.W)
//   val strb = UInt(cfg.strbWidth.W)
//   override def cloneType: this.type = new WChanLite(cfg).asInstanceOf[this.type]
// }

// class BChanLite(cfg: AXIConfig) extends Bundle {
//   val resp = UInt(cfg.respWidth.W)
//   override def cloneType: this.type = new BChanLite(cfg).asInstanceOf[this.type]
// }

// class ARChanLite(cfg: AXIConfig) extends Bundle {
//   val addr = UInt(cfg.addrWidth.W)
//   val prot = UInt(cfg.protWidth.W)
//   override def cloneType: this.type =
//     new ARChanLite(cfg).asInstanceOf[this.type]
// }

// class RChanLite(cfg: AXIConfig) extends Bundle {
//   val data = UInt(cfg.dataWidth.W)
//   val resp = UInt(cfg.respWidth.W)
//   override def cloneType: this.type = new RChanLite(cfg).asInstanceOf[this.type]
// }

// /** AXI-Lite Request bundle (master -> slave) */
// class AXILiteReqBundle(cfg: AXIConfig) extends Bundle {
//   val aw = new AWChanLite(cfg)
//   val aw_valid = Bool()
//   val w = new WChanLite(cfg)
//   val w_valid = Bool()
//   val b_ready = Bool()
//   val ar = new ARChanLite(cfg)
//   val ar_valid = Bool()
//   val r_ready = Bool()

//   override def cloneType: this.type =
//     new AXILiteReqBundle(cfg).asInstanceOf[this.type]
// }

// /** AXI-Lite Response bundle (slave -> master) */
// class AXILiteRespBundle(cfg: AXIConfig) extends Bundle {
//   val aw_ready = Bool()
//   val w_ready = Bool()
//   val b = new BChanLite(cfg)
//   val b_valid = Bool()
//   val ar_ready = Bool()
//   val r = new RChanLite(cfg)
//   val r_valid = Bool()

//   override def cloneType: this.type =
//     new AXILiteRespBundle(cfg).asInstanceOf[this.type]
// }

// ///////////////////////////////////////////////////////////////////////////////
// // Convenience factories (similar in spirit to your AXI_TYPEDEF_ALL macros)
// ///////////////////////////////////////////////////////////////////////////////
// object AXI {
//   def makeReq(cfg: AXIConfig = AXIConfig.default): AXIReqBundle =
//     new AXIReqBundle(cfg)
//   def makeResp(cfg: AXIConfig = AXIConfig.default): AXIRespBundle =
//     new AXIRespBundle(cfg)

//   def makeLiteReq(cfg: AXIConfig = AXIConfig.default): AXILiteReqBundle =
//     new AXILiteReqBundle(cfg)
//   def makeLiteResp(cfg: AXIConfig = AXIConfig.default): AXILiteRespBundle =
//     new AXILiteRespBundle(cfg)
// }

// ///////////////////////////////////////////////////////////////////////////////
// // Example usage snippet (for reference)
// // class Example extends Module {
// //   val cfg = AXIConfig(idWidth = 6, addrWidth = 32, dataWidth = 128, strbWidth = 16, userWidth = 8)
// //   val io = IO(new Bundle {
// //     val masterReq  = Flipped(AXI.makeReq(cfg))   // as seen by an AXI slave (master->slave requests)
// //     val masterResp = AXI.makeResp(cfg)           // responses back to master (slave->master)
// //   })
// // }
// ///////////////////////////////////////////////////////////////////////////////
