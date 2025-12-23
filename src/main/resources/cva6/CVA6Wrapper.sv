module cva6_wrapper #(
  parameter AXI_ADDRESS_WIDTH = 0,
  parameter AXI_DATA_WIDTH = 0,
  parameter AXI_USER_WIDTH = 0,
  parameter AXI_ID_WIDTH = 0
) (
    input clk_i,
    input rst_ni,
    input [63:0] boot_addr_i,
    input [31:0] hart_id_i,

    input  axi_aw_ready,
    output axi_aw_valid,
    output [AXI_ID_WIDTH-1:0] axi_aw_bits_id,
    output [AXI_ADDRESS_WIDTH-1:0] axi_aw_bits_addr,
    output [7:0] axi_aw_bits_len,
    output [2:0] axi_aw_bits_size,
    output [1:0] axi_aw_bits_burst,
    output axi_aw_bits_lock,
    output [3:0] axi_aw_bits_cache,
    output [2:0] axi_aw_bits_prot,
    output [3:0] axi_aw_bits_qos,
    output [3:0] axi_aw_bits_region,
    output [5:0] axi_aw_bits_atop,
    output [AXI_USER_WIDTH-1:0] axi_aw_bits_user,

    input axi_w_ready,
    output axi_w_valid,
    output [AXI_DATA_WIDTH-1:0] axi_w_bits_data,
    output [(AXI_DATA_WIDTH/8)-1:0] axi_w_bits_strb,
    output axi_w_bits_last,
    output [AXI_USER_WIDTH-1:0] axi_w_bits_user,

    input axi_ar_ready,
    output axi_ar_valid,
    output [AXI_ID_WIDTH-1:0] axi_ar_bits_id,
    output [AXI_ADDRESS_WIDTH-1:0] axi_ar_bits_addr,
    output [7:0] axi_ar_bits_len,
    output [2:0] axi_ar_bits_size,
    output [1:0] axi_ar_bits_burst,
    output axi_ar_bits_lock,
    output [3:0] axi_ar_bits_cache,
    output [2:0] axi_ar_bits_prot,
    output [3:0] axi_ar_bits_qos,
    output [3:0] axi_ar_bits_region,
    output [AXI_USER_WIDTH-1:0] axi_ar_bits_user,

    output axi_b_ready,
    input axi_b_valid,
    input [AXI_ID_WIDTH-1:0] axi_b_bits_id,
    input [1:0] axi_b_bits_resp,
    input [AXI_USER_WIDTH-1:0] axi_b_bits_user,

    output axi_r_ready,
    input axi_r_valid,
    input [AXI_ID_WIDTH-1:0] axi_r_bits_id,
    input [AXI_DATA_WIDTH-1:0] axi_r_bits_data,
    input [1:0] axi_r_bits_resp,
    input axi_r_bits_last,
    input [AXI_USER_WIDTH-1:0] axi_r_bits_user
);

    parameter type axi_ar_chan_t = struct packed {
      logic [AXI_ID_WIDTH-1:0]   id;
      logic [AXI_ADDRESS_WIDTH-1:0] addr;
      axi_pkg::len_t                   len;
      axi_pkg::size_t                  size;
      axi_pkg::burst_t                 burst;
      logic                            lock;
      axi_pkg::cache_t                 cache;
      axi_pkg::prot_t                  prot;
      axi_pkg::qos_t                   qos;
      axi_pkg::region_t                region;
      logic [AXI_USER_WIDTH-1:0] user;
    };
    parameter type axi_aw_chan_t = struct packed {
      logic [AXI_ID_WIDTH-1:0]   id;
      logic [AXI_ADDRESS_WIDTH-1:0] addr;
      axi_pkg::len_t                   len;
      axi_pkg::size_t                  size;
      axi_pkg::burst_t                 burst;
      logic                            lock;
      axi_pkg::cache_t                 cache;
      axi_pkg::prot_t                  prot;
      axi_pkg::qos_t                   qos;
      axi_pkg::region_t                region;
      axi_pkg::atop_t                  atop;
      logic [AXI_USER_WIDTH-1:0] user;
    };
    parameter type axi_w_chan_t = struct packed {
      logic [AXI_DATA_WIDTH-1:0]     data;
      logic [(AXI_DATA_WIDTH/8)-1:0] strb;
      logic                                last;
      logic [AXI_USER_WIDTH-1:0]     user;
    };
    parameter type b_chan_t = struct packed {
      logic [AXI_ID_WIDTH-1:0]   id;
      axi_pkg::resp_t                  resp;
      logic [AXI_USER_WIDTH-1:0] user;
    };
    parameter type r_chan_t = struct packed {
      logic [AXI_ID_WIDTH-1:0]   id;
      logic [AXI_DATA_WIDTH-1:0] data;
      axi_pkg::resp_t                  resp;
      logic                            last;
      logic [AXI_USER_WIDTH-1:0] user;
    };
    parameter type noc_req_t = struct packed {
      axi_aw_chan_t aw;
      logic         aw_valid;
      axi_w_chan_t  w;
      logic         w_valid;
      logic         b_ready;
      axi_ar_chan_t ar;
      logic         ar_valid;
      logic         r_ready;
    };
    parameter type noc_resp_t = struct packed {
      logic    aw_ready;
      logic    ar_ready;
      logic    w_ready;
      logic    b_valid;
      b_chan_t b;
      logic    r_valid;
      r_chan_t r;
    };

    noc_req_t  axi_req;
    noc_resp_t axi_rsp;

    cva6 i_cva6 (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .boot_addr_i(boot_addr_i),
        .hart_id_i(hart_id_i),
        .irq_i('0),
        .ipi_i('0),
        .time_irq_i('0),
        .debug_req_i('0),
        .rvfi_probes_o(),
        .cvxif_req_o(),
        .cvxif_resp_i('0),
        .noc_req_o(axi_req),
        .noc_resp_i(axi_rsp)
      );

    // connect axi_master_bus to the outgoing signals
    // input  axi_aw_ready,
    assign axi_rsp.aw_ready = axi_aw_ready;
    // output axi_aw_valid,
    assign axi_aw_valid = axi_req.aw_valid;
    // output [AXI_ID_WIDTH-1:0] axi_aw_bits_id,
    assign axi_aw_bits_id = axi_req.aw.id;
    // output [AXI_ADDRESS_WIDTH-1:0] axi_aw_bits_addr,
    assign axi_aw_bits_addr = axi_req.aw.addr;
    // output [7:0] axi_aw_bits_len,
    assign axi_aw_bits_len = axi_req.aw.len;
    // output [2:0] axi_aw_bits_size,
    assign axi_aw_bits_size = axi_req.aw.size;
    // output [1:0] axi_aw_bits_burst,
    assign axi_aw_bits_burst = axi_req.aw.burst;
    // output axi_aw_bits_lock,
    assign axi_aw_bits_lock = axi_req.aw.lock;
    // output [3:0] axi_aw_bits_cache,
    assign axi_aw_bits_cache = axi_req.aw.cache;
    // output [2:0] axi_aw_bits_prot,
    assign axi_aw_bits_prot = axi_req.aw.prot;
    // output [3:0] axi_aw_bits_qos,
    assign axi_aw_bits_qos = axi_req.aw.qos;
    // output [3:0] axi_aw_bits_region,
    assign axi_aw_bits_region = axi_req.aw.region;
    // output [5:0] axi_aw_bits_atop,
    // TODO: what to do with atop?
    // output [AXI_USER_WIDTH-1:0] axi_aw_bits_user,
    assign axi_aw_bits_user = axi_req.aw.user;

    // input axi_w_ready,
    assign axi_rsp.w_ready = axi_w_ready;
    // output axi_w_valid,
    assign axi_w_valid = axi_req.w_valid;
    // output [AXI_DATA_WIDTH-1:0] axi_w_bits_data,
    assign axi_w_bits_data = axi_req.w.data;
    // output [(AXI_DATA_WIDTH/8)-1:0] axi_w_bits_strb,
    assign axi_w_bits_strb = axi_req.w.strb;
    // output axi_w_bits_last,
    assign axi_w_bits_last = axi_req.w.last;
    // output [AXI_USER_WIDTH-1:0] axi_w_bits_user,
    assign axi_w_bits_user = axi_req.w.user;

    // input axi_ar_ready,
    assign axi_rsp.ar_ready = axi_ar_ready;
    // output axi_ar_valid,
    assign axi_ar_valid = axi_req.ar_valid;
    assign axi_ar_bits_id = axi_req.ar.id;
    // output [AXI_ID_WIDTH-1:0] axi_ar_bits_id,
    assign axi_ar_bits_addr = axi_req.ar.addr;
    // output [AXI_ADDRESS_WIDTH-1:0] axi_ar_bits_addr,
    assign axi_ar_bits_len = axi_req.ar.len;
    // output [7:0] axi_ar_bits_len,
    assign axi_ar_bits_size = axi_req.ar.size;
    // output [2:0] axi_ar_bits_size,
    assign axi_ar_bits_burst = axi_req.ar.burst;
    // output [1:0] axi_ar_bits_burst,
    assign axi_ar_bits_lock = axi_req.ar.lock;
    // output axi_ar_bits_lock,
    assign axi_ar_bits_cache = axi_req.ar.cache;
    // output [3:0] axi_ar_bits_cache,
    assign axi_ar_bits_prot = axi_req.ar.prot;
    // output [2:0] axi_ar_bits_prot,
    assign axi_ar_bits_qos = axi_req.ar.qos;
    // output [3:0] axi_ar_bits_qos,
    assign axi_ar_bits_region = axi_req.ar.region;
    // output [3:0] axi_ar_bits_region,
    assign axi_ar_bits_user = axi_req.ar.user;
    // output [AXI_USER_WIDTH-1:0] axi_ar_bits_user,

    // output axi_b_ready,
    assign axi_b_ready = axi_req.b_ready;
    // output axi_ar_valid,
    assign axi_rsp.b_valid = axi_b_valid;
    // input axi_b_valid,
    assign axi_rsp.b.id = axi_b_bits_id;
    // input [AXI_ID_WIDTH-1:0] axi_b_bits_id,
    assign axi_rsp.b.resp = axi_b_bits_resp;
    // input [1:0] axi_b_bits_resp,
    assign axi_rsp.b.user = axi_b_bits_user;
    // input [AXI_USER_WIDTH-1:0] axi_b_bits_user,

    assign axi_r_ready = axi_req.r_ready;
    // output axi_r_ready,
    assign axi_rsp.r_valid = axi_r_valid;
    // input axi_r_valid,
    assign axi_rsp.r.id = axi_r_bits_id;
    // input [AXI_ID_WIDTH-1:0] axi_r_bits_id,
    assign axi_rsp.r.data = axi_r_bits_data;
    // input [AXI_DATA_WIDTH-1:0] axi_r_bits_data,
    assign axi_rsp.r.resp = axi_r_bits_resp;
    // input [1:0] axi_r_bits_resp,
    assign axi_rsp.r.last = axi_r_bits_last;
    // input axi_r_bits_last,
    assign axi_rsp.r.user = axi_r_bits_user;
    // input [AXI_USER_WIDTH-1:0] axi_r_bits_user
endmodule
