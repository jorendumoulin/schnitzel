module TopWrapper(
  input  logic clock,
  input  logic reset
);

  logic         wide_req_valid, wide_req_ready;
  logic [31:0]  wide_req_addr;
  logic [511:0] wide_req_wdata;
  logic         wide_req_wen;
  logic [63:0]  wide_req_ben;
  logic         wide_rsp_valid, wide_rsp_ready;
  logic [511:0] wide_rsp_data;

  logic         narrow_req_valid, narrow_req_ready;
  logic [31:0]  narrow_req_addr;
  logic [63:0]  narrow_req_wdata;
  logic         narrow_req_wen;
  logic [7:0]   narrow_req_ben;
  logic         narrow_rsp_valid, narrow_rsp_ready;
  logic [63:0]  narrow_rsp_data;

  Top top (
    .clock                            (clock),
    .reset                            (reset),
    .io_mem_req_ready                 (wide_req_ready),
    .io_mem_req_valid                 (wide_req_valid),
    .io_mem_req_bits_addr             (wide_req_addr),
    .io_mem_req_bits_wdata            (wide_req_wdata),
    .io_mem_req_bits_wen              (wide_req_wen),
    .io_mem_req_bits_ben              (wide_req_ben),
    .io_mem_rsp_ready                 (wide_rsp_ready),
    .io_mem_rsp_valid                 (wide_rsp_valid),
    .io_mem_rsp_bits_data             (wide_rsp_data),
    .io_narrow_mem_req_ready          (narrow_req_ready),
    .io_narrow_mem_req_valid          (narrow_req_valid),
    .io_narrow_mem_req_bits_addr      (narrow_req_addr),
    .io_narrow_mem_req_bits_wdata     (narrow_req_wdata),
    .io_narrow_mem_req_bits_wen       (narrow_req_wen),
    .io_narrow_mem_req_bits_ben       (narrow_req_ben),
    .io_narrow_mem_rsp_ready          (narrow_rsp_ready),
    .io_narrow_mem_rsp_valid          (narrow_rsp_valid),
    .io_narrow_mem_rsp_bits_data      (narrow_rsp_data)
  );

  MemDpi #(.DATA_WIDTH(512), .STRB_WIDTH(64)) wide_mem (
    .clock     (clock),
    .reset     (reset),
    .req_valid (wide_req_valid),
    .req_addr  (wide_req_addr),
    .req_wdata (wide_req_wdata),
    .req_wen   (wide_req_wen),
    .req_ben   (wide_req_ben),
    .req_ready (wide_req_ready),
    .rsp_valid (wide_rsp_valid),
    .rsp_data  (wide_rsp_data),
    .rsp_ready (wide_rsp_ready)
  );

  MemDpi #(.DATA_WIDTH(64), .STRB_WIDTH(8)) narrow_mem (
    .clock     (clock),
    .reset     (reset),
    .req_valid (narrow_req_valid),
    .req_addr  (narrow_req_addr),
    .req_wdata (narrow_req_wdata),
    .req_wen   (narrow_req_wen),
    .req_ben   (narrow_req_ben),
    .req_ready (narrow_req_ready),
    .rsp_valid (narrow_rsp_valid),
    .rsp_data  (narrow_rsp_data),
    .rsp_ready (narrow_rsp_ready)
  );

endmodule
