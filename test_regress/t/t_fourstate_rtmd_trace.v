// DESCRIPTION: Verilator: RTMD value/XZ address, slice and resume regressions
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps
`define STRINGIFY(x) `"x`"
module t;
  bit [1:0] phase;
  rtmd_lane #(1) w1(phase);
  rtmd_lane #(8) w8(phase);
  rtmd_lane #(9) w9(phase);
  rtmd_lane #(32) w32(phase);
  rtmd_lane #(33) w33(phase);
  rtmd_lane #(64) w64(phase);
  rtmd_lane #(65) w65(phase);
  rtmd_lane #(128) w128(phase);
  rtmd_lane #(129) w129(phase);
  rtmd_lane #(256) w256(phase);
  rtmd_lane #(257) w257(phase);
  rtmd_lane #(301) w301(phase);

  typedef struct packed {
    logic [64:0] cross_word;
    logic [30:0] tail;
  } wide_slice_t;
  typedef struct packed {
    logic [32:0] cross_word;
    logic [30:0] tail;
  } small_slice_t;
  wide_slice_t wide_slice;
  small_slice_t small_slice;
  assign wide_slice = {w129.a[95:31], w129.a[30:0]};
  assign small_slice = {w129.a[63:31], w129.a[30:0]};
  initial begin
    phase = 0;
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars;
    #5 phase = 1;  // Only XZ changes: all ones become all X.
    #6 phase = 2;
    #7 phase = 3;  // Only XZ changes: all zeroes become all Z.
    #8 phase = 0;
    #9 phase = 1;  // Repeat after coroutine suspension and resumption.
    #9;
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module rtmd_lane #(parameter W = 1)(input bit [1:0] phase);
  wire [W-1:0] a = phase[1] ? (phase[0] ? 'z : '0) : (phase[0] ? 'x : '1);
  wire [W-1:0] opposite = phase[1] ? (phase[0] ? '0 : 'z) : (phase[0] ? '1 : 'x);
  wire [W-1:0] real_alias = a;
endmodule
