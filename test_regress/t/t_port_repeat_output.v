// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps
// Deliberate ascending declarations verify logical bit positions.
// verilator lint_off ASCRANGE
module repeat_output #(parameter integer W = 13,
                       parameter integer LEFT = W - 1,
                       parameter integer RIGHT = 0) (o, o, d);
  output wire [LEFT:RIGHT] o;
  input wire [W-1:0] d;
  assign o = d;
endmodule
module unique_output(input wire [32:0] d, output wire [32:0] q);
  assign q = d;
endmodule
module t (
    output wire [18:6] a13_left, a13_right, b13_left, b13_right,
    output wire [4:34] a31_left, b31_left,
    output wire [34:4] a31_right, b31_right,
    output wire [40:8] a33_left, b33_left,
    output wire [8:40] a33_right, b33_right,
    output wire [32:0] unique33
);
  // verilator lint_on ASCRANGE
  integer unsigned checks = 0;
  // verilog_format: off
  `define stop $stop
  `define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
  `define CHECK(gotv, expv, labelv) begin `checkh(gotv, expv); $display("PORT_REPEAT_OUTPUT_CHECK n=%0d label=%s got=%b", checks, labelv, gotv); end
  // verilog_format: on

  reg [12:0] d_a13, d_b13;
  reg [30:0] d_a31, d_b31;
  reg [32:0] d_a33, d_b33, d_unique;
  // Equal parameterizations share the module definition but have separate state.
  repeat_output #(13, 18, 6) u13a(a13_left, a13_right, d_a13);
  repeat_output #(13, 18, 6) u13b(b13_left, b13_right, d_b13);
  repeat_output #(31, 4, 34) u31a(a31_left, a31_right, d_a31);
  repeat_output #(31, 4, 34) u31b(b31_left, b31_right, d_b31);
  repeat_output #(33, 40, 8) u33a(a33_left, a33_right, d_a33);
  repeat_output #(33, 40, 8) u33b(b33_left, b33_right, d_b33);
  unique_output unique_control(d_unique, unique33);

  initial begin
    // Phase0: independently frozen literals for both instances.
    d_a13 = 13'b0000000000000;
    d_b13 = 13'b1111111111111;
    d_a31 = 31'b0000000000000000000000000000000;
    d_b31 = 31'b1111111111111111111111111111111;
    d_a33 = 33'b000000000000000000000000000000000;
    d_b33 = 33'b111111111111111111111111111111111;
    d_unique = 33'b000000000000000000000000000000000;
    #1;
    `CHECK(a13_left, 13'b0000000000000, "p0_a13_left");
    `CHECK(a13_right, 13'b0000000000000, "p0_a13_right");
    `CHECK(b13_left, 13'b1111111111111, "p0_b13_left");
    `CHECK(b13_right, 13'b1111111111111, "p0_b13_right");
    `CHECK(a31_left, 31'b0000000000000000000000000000000, "p0_a31_left");
    `CHECK(a31_right, 31'b0000000000000000000000000000000, "p0_a31_right");
    `CHECK(b31_left, 31'b1111111111111111111111111111111, "p0_b31_left");
    `CHECK(b31_right, 31'b1111111111111111111111111111111, "p0_b31_right");
    `CHECK(a33_left, 33'b000000000000000000000000000000000, "p0_a33_left");
    `CHECK(a33_right, 33'b000000000000000000000000000000000, "p0_a33_right");
    `CHECK(b33_left, 33'b111111111111111111111111111111111, "p0_b33_left");
    `CHECK(b33_right, 33'b111111111111111111111111111111111, "p0_b33_right");
    `CHECK(unique33, 33'b000000000000000000000000000000000, "p0_unique33");
    // Phase1: independently frozen literals for both instances.
    d_a13 = 13'b1111111111111;
    d_b13 = 13'b0000000000000;
    d_a31 = 31'b1111111111111111111111111111111;
    d_b31 = 31'b0000000000000000000000000000000;
    d_a33 = 33'b111111111111111111111111111111111;
    d_b33 = 33'b000000000000000000000000000000000;
    d_unique = 33'b111111111111111111111111111111111;
    #1;
    `CHECK(a13_left, 13'b1111111111111, "p1_a13_left");
    `CHECK(a13_right, 13'b1111111111111, "p1_a13_right");
    `CHECK(b13_left, 13'b0000000000000, "p1_b13_left");
    `CHECK(b13_right, 13'b0000000000000, "p1_b13_right");
    `CHECK(a31_left, 31'b1111111111111111111111111111111, "p1_a31_left");
    `CHECK(a31_right, 31'b1111111111111111111111111111111, "p1_a31_right");
    `CHECK(b31_left, 31'b0000000000000000000000000000000, "p1_b31_left");
    `CHECK(b31_right, 31'b0000000000000000000000000000000, "p1_b31_right");
    `CHECK(a33_left, 33'b111111111111111111111111111111111, "p1_a33_left");
    `CHECK(a33_right, 33'b111111111111111111111111111111111, "p1_a33_right");
    `CHECK(b33_left, 33'b000000000000000000000000000000000, "p1_b33_left");
    `CHECK(b33_right, 33'b000000000000000000000000000000000, "p1_b33_right");
    `CHECK(unique33, 33'b111111111111111111111111111111111, "p1_unique33");
    // Phase2: independently frozen literals for both instances.
    d_a13 = 13'bxxxxxxxxxxxxx;
    d_b13 = 13'bzzzzzzzzzzzzz;
    d_a31 = 31'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx;
    d_b31 = 31'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz;
    d_a33 = 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx;
    d_b33 = 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz;
    d_unique = 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx;
    #1;
    `CHECK(a13_left, 13'bxxxxxxxxxxxxx, "p2_a13_left");
    `CHECK(a13_right, 13'bxxxxxxxxxxxxx, "p2_a13_right");
    `CHECK(b13_left, 13'bzzzzzzzzzzzzz, "p2_b13_left");
    `CHECK(b13_right, 13'bzzzzzzzzzzzzz, "p2_b13_right");
    `CHECK(a31_left, 31'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p2_a31_left");
    `CHECK(a31_right, 31'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p2_a31_right");
    `CHECK(b31_left, 31'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p2_b31_left");
    `CHECK(b31_right, 31'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p2_b31_right");
    `CHECK(a33_left, 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p2_a33_left");
    `CHECK(a33_right, 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p2_a33_right");
    `CHECK(b33_left, 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p2_b33_left");
    `CHECK(b33_right, 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p2_b33_right");
    `CHECK(unique33, 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p2_unique33");
    // Phase3: independently frozen literals for both instances.
    d_a13 = 13'bzzzzzzzzzzzzz;
    d_b13 = 13'bxxxxxxxxxxxxx;
    d_a31 = 31'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz;
    d_b31 = 31'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx;
    d_a33 = 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz;
    d_b33 = 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx;
    d_unique = 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz;
    #1;
    `CHECK(a13_left, 13'bzzzzzzzzzzzzz, "p3_a13_left");
    `CHECK(a13_right, 13'bzzzzzzzzzzzzz, "p3_a13_right");
    `CHECK(b13_left, 13'bxxxxxxxxxxxxx, "p3_b13_left");
    `CHECK(b13_right, 13'bxxxxxxxxxxxxx, "p3_b13_right");
    `CHECK(a31_left, 31'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p3_a31_left");
    `CHECK(a31_right, 31'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p3_a31_right");
    `CHECK(b31_left, 31'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p3_b31_left");
    `CHECK(b31_right, 31'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p3_b31_right");
    `CHECK(a33_left, 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p3_a33_left");
    `CHECK(a33_right, 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p3_a33_right");
    `CHECK(b33_left, 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p3_b33_left");
    `CHECK(b33_right, 33'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, "p3_b33_right");
    `CHECK(unique33, 33'bzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz, "p3_unique33");
    // Phase4: independently frozen literals for both instances.
    d_a13 = 13'b10xz01zx10xz0;
    d_b13 = 13'b01zx10xz01zx1;
    d_a31 = 31'b10xz01zx10xz01zx10xz01zx10xz01z;
    d_b31 = 31'b01zx10xz01zx10xz01zx10xz01zx10x;
    d_a33 = 33'b10xz01zx10xz01zx10xz01zx10xz01zx1;
    d_b33 = 33'b01zx10xz01zx10xz01zx10xz01zx10xz0;
    d_unique = 33'b1000000000000000xz111111111111111;
    #1;
    `CHECK(a13_left, 13'b10xz01zx10xz0, "p4_a13_left");
    `CHECK(a13_right, 13'b10xz01zx10xz0, "p4_a13_right");
    `CHECK(b13_left, 13'b01zx10xz01zx1, "p4_b13_left");
    `CHECK(b13_right, 13'b01zx10xz01zx1, "p4_b13_right");
    `CHECK(a31_left, 31'b10xz01zx10xz01zx10xz01zx10xz01z, "p4_a31_left");
    `CHECK(a31_right, 31'b10xz01zx10xz01zx10xz01zx10xz01z, "p4_a31_right");
    `CHECK(b31_left, 31'b01zx10xz01zx10xz01zx10xz01zx10x, "p4_b31_left");
    `CHECK(b31_right, 31'b01zx10xz01zx10xz01zx10xz01zx10x, "p4_b31_right");
    `CHECK(a33_left, 33'b10xz01zx10xz01zx10xz01zx10xz01zx1, "p4_a33_left");
    `CHECK(a33_right, 33'b10xz01zx10xz01zx10xz01zx10xz01zx1, "p4_a33_right");
    `CHECK(b33_left, 33'b01zx10xz01zx10xz01zx10xz01zx10xz0, "p4_b33_left");
    `CHECK(b33_right, 33'b01zx10xz01zx10xz01zx10xz01zx10xz0, "p4_b33_right");
    `CHECK(unique33, 33'b1000000000000000xz111111111111111, "p4_unique33");
    `CHECK(a13_left[18], 1'b1, "p4_a13_left_bit18");
    `CHECK(a13_left[6], 1'b0, "p4_a13_left_bit6");
    `CHECK(a13_right[18], 1'b1, "p4_a13_right_bit18");
    `CHECK(a13_right[6], 1'b0, "p4_a13_right_bit6");
    `CHECK(a31_left[4], 1'b1, "p4_a31_left_bit4");
    `CHECK(a31_left[34], 1'bz, "p4_a31_left_bit34");
    `CHECK(a31_right[34], 1'b1, "p4_a31_right_bit34");
    `CHECK(a31_right[4], 1'bz, "p4_a31_right_bit4");
    `CHECK(a33_left[40], 1'b1, "p4_a33_left_bit40");
    `CHECK(a33_left[8], 1'b1, "p4_a33_left_bit8");
    `CHECK(a33_right[8], 1'b1, "p4_a33_right_bit8");
    `CHECK(a33_right[40], 1'b1, "p4_a33_right_bit40");
    // Phase5: independently frozen literals for both instances.
    d_a13 = 13'b1000000000000;
    d_b13 = 13'b0000000000001;
    d_a31 = 31'b1000000000000000000000000000000;
    d_b31 = 31'b0000000000000000000000000000001;
    d_a33 = 33'b100000000000000000000000000000000;
    d_b33 = 33'b000000000000000000000000000000001;
    d_unique = 33'b000000000000000000000000000000001;
    #1;
    `CHECK(a13_left, 13'b1000000000000, "p5_a13_left");
    `CHECK(a13_right, 13'b1000000000000, "p5_a13_right");
    `CHECK(b13_left, 13'b0000000000001, "p5_b13_left");
    `CHECK(b13_right, 13'b0000000000001, "p5_b13_right");
    `CHECK(a31_left, 31'b1000000000000000000000000000000, "p5_a31_left");
    `CHECK(a31_right, 31'b1000000000000000000000000000000, "p5_a31_right");
    `CHECK(b31_left, 31'b0000000000000000000000000000001, "p5_b31_left");
    `CHECK(b31_right, 31'b0000000000000000000000000000001, "p5_b31_right");
    `CHECK(a33_left, 33'b100000000000000000000000000000000, "p5_a33_left");
    `CHECK(a33_right, 33'b100000000000000000000000000000000, "p5_a33_right");
    `CHECK(b33_left, 33'b000000000000000000000000000000001, "p5_b33_left");
    `CHECK(b33_right, 33'b000000000000000000000000000000001, "p5_b33_right");
    `CHECK(unique33, 33'b000000000000000000000000000000001, "p5_unique33");
    `CHECK(a13_left[18], 1'b1, "p5_a13_left_bit18");
    `CHECK(a13_left[6], 1'b0, "p5_a13_left_bit6");
    `CHECK(a13_right[18], 1'b1, "p5_a13_right_bit18");
    `CHECK(a13_right[6], 1'b0, "p5_a13_right_bit6");
    `CHECK(a31_left[4], 1'b1, "p5_a31_left_bit4");
    `CHECK(a31_left[34], 1'b0, "p5_a31_left_bit34");
    `CHECK(a31_right[34], 1'b1, "p5_a31_right_bit34");
    `CHECK(a31_right[4], 1'b0, "p5_a31_right_bit4");
    `CHECK(a33_left[40], 1'b1, "p5_a33_left_bit40");
    `CHECK(a33_left[8], 1'b0, "p5_a33_left_bit8");
    `CHECK(a33_right[8], 1'b1, "p5_a33_right_bit8");
    `CHECK(a33_right[40], 1'b0, "p5_a33_right_bit40");
    $display("PORT_REPEAT_OUTPUT checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
