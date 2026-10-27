// DESCRIPTION: Verilator: Four-state ancestor task arguments, outputs and parent state
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps
module xz_leaf(input wire [7:0] token, output reg [7:0] first, second);
  initial begin
    #5; emit(token, first);
    #2; emit(~token, second);
  end
endmodule
module xz_mid(input wire [7:0] token, output wire [7:0] first, second);
  xz_leaf leaf(token, first, second);
endmodule
module xz_nearest(input wire [7:0] token, output wire [7:0] first, second);
  reg [7:0] calls = 0;
  reg [7:0] last = 0;
  task emit(input [7:0] arg, output [7:0] value);
    calls = calls + 8'd1;
    last = arg;
    value = {arg[7:4], arg[7:4]};
  endtask
  xz_leaf leaf(token, first, second);
endmodule
module xz_parent_a(input wire [7:0] token,
                   output wire [7:0] first, second, near_first, near_second);
  reg [7:0] calls = 0;
  reg [7:0] last = 0;
  task emit(input [7:0] arg, output [7:0] value);
    calls = calls + 8'd1;
    last = arg;
    value = arg ^ 8'h10;
  endtask
  xz_mid bridge(token, first, second);
  xz_nearest near0(token, near_first, near_second);
endmodule
module xz_parent_b(input wire [7:0] token, output wire [7:0] first, second);
  reg [7:0] calls = 0;
  reg [7:0] last = 0;
  task emit(input [7:0] arg, output [7:0] value);
    calls = calls + 8'd1;
    last = arg;
    value = {arg[3:0], arg[7:4]};
  endtask
  xz_mid bridge(token, first, second);
endmodule
module t;
  integer checks = 0;
  // verilog_format: off
  `define CHECK(actual, expected, check_label) \
    begin \
      checks = checks + 1; \
      if ((actual) !== (expected)) $fatal(1, check_label); \
      $display("ANCESTOR_XZ_CHECK n=%0d label=%s got=%b", checks, check_label, actual); \
    end
  // verilog_format: on
  wire [7:0] a0, a1, n0, n1, a2, a3, n2, n3, b0, b1;
  xz_parent_a a(8'b10xz_01zx, a0, a1, n0, n1);
  xz_parent_a aa(8'b01zx_10xz, a2, a3, n2, n3);
  xz_parent_b b(8'bx1z0_zx10, b0, b1);
  initial begin
    #6;
    `CHECK(a0, 8'b10xx_01xx, "a_first")
    `CHECK(a2, 8'b01xx_10xx, "aa_first")
    `CHECK(b0, 8'bzx10_x1z0, "b_first")
    `CHECK(n0, 8'b10xz_10xz, "a_nearest_first")
    `CHECK(n2, 8'b01zx_01zx, "aa_nearest_first")
    `CHECK(a.last, 8'b10xz_01zx, "a_first_state")
    `CHECK(aa.last, 8'b01zx_10xz, "aa_first_state")
    `CHECK(b.last, 8'bx1z0_zx10, "b_first_state")
    `CHECK(a.near0.last, 8'b10xz_01zx, "a_nearest_first_state")
    `CHECK(aa.near0.last, 8'b01zx_10xz, "aa_nearest_first_state")
    `CHECK(a.calls, 8'd1, "a_first_calls")
    `CHECK(aa.calls, 8'd1, "aa_first_calls")
    `CHECK(b.calls, 8'd1, "b_first_calls")
    `CHECK(a.near0.calls, 8'd1, "a_nearest_first_calls")
    `CHECK(aa.near0.calls, 8'd1, "aa_nearest_first_calls")
    #2;
    `CHECK(a1, 8'b01xx_10xx, "a_second")
    `CHECK(a3, 8'b10xx_01xx, "aa_second")
    `CHECK(b1, 8'bxx01_x0x1, "b_second")
    `CHECK(n1, 8'b01xx_01xx, "a_nearest_second")
    `CHECK(n3, 8'b10xx_10xx, "aa_nearest_second")
    `CHECK(a.last, 8'b01xx_10xx, "a_second_state")
    `CHECK(aa.last, 8'b10xx_01xx, "aa_second_state")
    `CHECK(b.last, 8'bx0x1_xx01, "b_second_state")
    `CHECK(a.near0.last, 8'b01xx_10xx, "a_nearest_second_state")
    `CHECK(aa.near0.last, 8'b10xx_01xx, "aa_nearest_second_state")
    `CHECK(a.calls, 8'd2, "a_second_calls")
    `CHECK(aa.calls, 8'd2, "aa_second_calls")
    `CHECK(b.calls, 8'd2, "b_second_calls")
    `CHECK(a.near0.calls, 8'd2, "a_nearest_second_calls")
    `CHECK(aa.near0.calls, 8'd2, "aa_nearest_second_calls")
    if (checks != 30) $fatal(1, "missing XZ checks");
    $display("ANCESTOR_XZ checks=%0d", checks);
    `undef CHECK
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
