// DESCRIPTION: Verilator: Wide signed constants index negative packed array ranges
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [2:0] done;
  packed_wide_index_width #(32) w32 (done[0]);
  packed_wide_index_width #(65) w65 (done[1]);
  packed_wide_index_width #(95) w95 (done[2]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #2500;
    if (done !== '1) $fatal(1, "Packed wide signed index checks did not finish");
    $display("Packed wide signed index checks: %0d", w32.checks + w65.checks + w95.checks);
    $display("PASS packed_array_index_wide_signed");
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module packed_wide_index_width #(
    parameter int INDEX_WIDTH = 32
) (
    output bit done = 0
);
  localparam logic signed [INDEX_WIDTH-1:0] MINUS_ONE = -1;
  localparam logic signed [INDEX_WIDTH-1:0] MINUS_TWO = -2;
  localparam logic signed [INDEX_WIDTH-1:0] MINUS_THREE = -3;
  logic [-1:-3][6:0] data = '0;
  wire [6:0] out_one = data[MINUS_ONE];
  wire [6:0] out_two = data[MINUS_TWO];
  wire [6:0] out_three = data[MINUS_THREE];
  bit [31:0] checks = 0;

  initial begin
    #1000;
    data = {7'h55, 7'h2a, 7'h13};
    #1;
    `checkh(out_one, 7'h55)
    `checkh(out_two, 7'h2a)
    `checkh(out_three, 7'h13)
    #999;
    data = {7'b101x001, 7'bx010110, 7'b11010xx};
    #1;
    `checkh(out_one, 7'b101x001)
    `checkh(out_two, 7'bx010110)
    `checkh(out_three, 7'b11010xx)
    done = 1;
  end
endmodule
