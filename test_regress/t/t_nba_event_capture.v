// DESCRIPTION: Verilator: No-timing NBA event index and payload capture
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0)
// verilog_format: on

module t (
    input bit route,
    input bit pattern,
    output bit [31:0] count0,
    output bit [31:0] count1,
    output bit capture_ok
);
`ifdef NBA_EVENT_CAPTURE_KNOWN
  localparam logic [7:0] DATA0 = 8'h49;
  localparam logic [7:0] DATA1 = 8'hb6;
`else
  localparam logic [7:0] DATA0 = 8'bz1x0101x;
  localparam logic [7:0] DATA1 = 8'b10xz01z1;
`endif
  event ready[2];
  logic [7:0] value;
  logic [7:0] rhs;
  int idx;

  initial begin
    count0 = 0;
    count1 = 0;
    capture_ok = 0;
    value = 0;
    rhs = pattern ? DATA1 : DATA0;
    idx = int'(route);
    // Both updates are scheduled before changing either captured input.
    value <= rhs;
    ->>ready[idx];
    idx = 1;
    rhs = 0;
  end

  always @(ready[0]) begin
    count0++;
    `checkh(value, pattern ? DATA1 : DATA0);
    capture_ok = 1;
  end
  always @(ready[1]) count1++;
endmodule
