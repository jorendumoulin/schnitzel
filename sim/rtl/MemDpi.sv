module MemDpi #(
  parameter DATA_WIDTH = 512,
  parameter STRB_WIDTH = DATA_WIDTH/8
)(
  input  logic                       clock,
  input  logic                       reset,
  input  logic                       req_valid,
  input  logic [31:0]                req_addr,
  input  logic [DATA_WIDTH-1:0]      req_wdata,
  input  logic                       req_wen,
  input  logic [STRB_WIDTH-1:0]      req_ben,
  output logic                       req_ready,
  output logic                       rsp_valid,
  output logic [DATA_WIDTH-1:0]      rsp_data,
  input  logic                       rsp_ready
);

  // --- Internal State ---
  logic rsp_valid_q;
  logic [DATA_WIDTH-1:0] rsp_data_q;

  assign req_ready = !rsp_valid_q || rsp_ready;
  assign rsp_valid = rsp_valid_q;
  assign rsp_data  = rsp_data_q;

  // --- DPI Imports ---
  import "DPI-C" function void dpi_mem_read_512(input int addr, output bit [511:0] data);
  import "DPI-C" function void dpi_mem_write_512(input int addr, input bit [511:0] data, input bit [63:0] ben);
  import "DPI-C" function void dpi_mem_read_64(input int addr, output bit [63:0] data);
  import "DPI-C" function void dpi_mem_write_64(input int addr, input bit [63:0] data, input bit [7:0] ben);
  // --- Sequential Logic ---
  always_ff @(posedge clock) begin
    if (reset) begin
      rsp_valid_q <= 1'b0;
      rsp_data_q  <= '0;
    end else begin
      if (req_valid && req_ready) begin
        rsp_valid_q <= 1'b1;

        if (req_wen) begin
          // WRITE Logic
          if (DATA_WIDTH == 512) begin
            dpi_mem_write_512(req_addr, req_wdata, req_ben);
          end else begin
            dpi_mem_write_64(req_addr, req_wdata, req_ben);
          end

          rsp_data_q <= req_wdata;
          // $display("[%0t] [MemDpi] WRITE Addr: 0x%h, Data: 0x%h", $time, req_addr, req_wdata);

        end else begin
          // READ Logic
          // Use a temporary variable for DPI output to avoid issues with
          // older Verilator versions (< 5.044) not correctly propagating
          // DPI output arguments that target flip-flop registers directly.
          begin
            logic [DATA_WIDTH-1:0] tmp_data;
            if (DATA_WIDTH == 512) begin
              dpi_mem_read_512(req_addr, tmp_data);
            end else begin
              dpi_mem_read_64(req_addr, tmp_data);
            end
            rsp_data_q <= tmp_data;
            // $display("[%0t] [MemDpi] READ  Addr: 0x%h, Data: 0x%h", $time, req_addr, tmp_data);
          end
        end
      end else if (rsp_ready) begin
        rsp_valid_q <= 1'b0;
      end
    end
  end

endmodule
