//// package core
////
//// import chisel3._
//// import chisel3.util.HasBlackBoxResource
//// import chisel3.util.Fill
//// import chisel3.util.Counter
//// import csr.CsrIO
//// import csr.CsrOp
//// import axi.AXIBundle
//// import axi.AXIConfig
////
//// class BigCore extends Module {
////
//// val io = IO(new Bundle {
//// val axi = new AXIBundle(new AXIConfig);
//// })
////
//// val rocket = Module(new rocket_wrapper())
////
//// val io_aggregator_5_clock = Input(Clock())
//// val io_aggregator_5_reset = Input(Bool())
//// val io_aggregator_4_clock = Input(Clock())
//// val io_aggregator_4_reset = Input(Bool())
//// val io_aggregator_3_clock = Input(Clock())
//// val io_aggregator_3_reset = Input(Bool())
//// val io_aggregator_2_clock = Input(Clock())
//// val io_aggregator_2_reset = Input(Bool())
//// val io_aggregator_1_clock = Input(Clock())
//// val io_aggregator_1_reset = Input(Bool())
//// val io_aggregator_0_clock = Input(Clock())
//// val io_aggregator_0_reset = Input(Bool())
//// val resetctrl_hartIsInReset_0 = Input(Bool())
//// val debug_clock = Input(Clock())
//// val debug_reset = Input(Bool())
////
//// val debug_clocked_dmi = new DebugDmi
////
//// rocket.io.io := clock
//// reset.io.rst_ni := ~reset.asBool
////
//// ibex.io.hart_id_i := hartId.U
//// ibex.io.boot_addr_i := 0x1000.U
////
//Instruction memory interface
//// io.imem.req.valid := ibex.io.instr_req_o
//// io.imem.req.bits.addr := ibex.io.instr_addr_o
//// io.imem.req.bits.wen := false.B
//// io.imem.req.bits.ben := Fill(4, 1.U);
//// io.imem.req.bits.wdata := 0.U
//// io.imem.rsp.ready := true.B
//// ibex.io.instr_gnt_i := io.imem.req.ready
//// ibex.io.instr_rvalid_i := io.imem.rsp.valid
//// ibex.io.instr_rdata_i := io.imem.rsp.bits.data
//// ibex.io.instr_err_i := 0.U
////
//Data memory interface
//// io.dmem.req.valid := ibex.io.data_req_o
//// io.dmem.req.bits.addr := ibex.io.data_addr_o
//// io.dmem.req.bits.wen := ibex.io.data_we_o
//// io.dmem.req.bits.ben := ibex.io.data_be_o
//// io.dmem.req.bits.wdata := ibex.io.data_wdata_o
//// ibex.io.data_gnt_i := io.dmem.req.ready
//// io.dmem.rsp.ready := true.B
//// ibex.io.data_rvalid_i := io.dmem.rsp.valid
//// ibex.io.data_rdata_i := io.dmem.rsp.bits.data
//// ibex.io.data_err_i := 0.U
////
//// val (_, counterWrap) = Counter(ibex.io.csr_ext_valid_o, 4)
////
//CSR interface
//// ibex.io.csr_ext_ready_i := io.csr.req.ready
//// io.csr.req.valid := ibex.io.csr_ext_valid_o
//// io.csr.req.bits.addr := ibex.io.csr_ext_addr_o
//// io.csr.req.bits.wdata := ibex.io.csr_ext_wdata_o
//// io.csr.req.bits.op := ibex.io.csr_ext_op_o.asTypeOf(io.csr.req.bits.op)
//// ibex.io.csr_ext_rdata_i := io.csr.rsp.rdata
////
//// }
////
