// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkr(gotv,expv) do begin checks++; if ((gotv) != (expv)) begin $write("%%Error: %s:%0d: got=%0f expected=%0f\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  bit scalar = 0;
  bit [128:0] vector = '0;
  bit [7:0] control = 0;
  bit [31:0] checks = 0;
  time scalar_time = 0, vector_time = 0;
  realtime scalar_real = 0.0, vector_real = 0.0;
  time combo_time;
  realtime combo_real;

  // These observers have no data read besides the time query.
  always @(scalar) scalar_time = $time;
  always @(scalar) scalar_real = $realtime;
  always @(vector) vector_time = $time;
  always @(vector) vector_real = $realtime;

  // Implicit sensitivity still follows an ordinary input used by the body.
  always_comb combo_time = $time ^ 64'(control);
  always_comb combo_real = $realtime + real'(control);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #1.25;
    scalar = 1;
    vector[128] = 1;
    control = 8'h22;
    #0.125;
    `checkd(scalar_time, 64'd1);
    `checkd(vector_time, 64'd1);
    `checkr(scalar_real, 1.25);
    `checkr(vector_real, 1.25);
    `checkd(combo_time, 64'd35);
    `checkr(combo_real, 35.25);
    #0.625;
    scalar = 0;
    vector[64] = 1;
    control = 8'h13;
    #0.125;
    `checkd(scalar_time, 64'd2);
    `checkd(vector_time, 64'd2);
    `checkr(scalar_real, 2.0);
    `checkr(vector_real, 2.0);
    `checkd(combo_time, 64'd17);
    `checkr(combo_real, 21.0);
    #0.875;
    vector[32] = 1;
    control = 8'h26;
    #0.125;
    `checkd(scalar_time, 64'd2);
    `checkd(vector_time, 64'd3);
    `checkr(scalar_real, 2.0);
    `checkr(vector_real, 3.0);
    `checkd(combo_time, 64'd37);
    `checkr(combo_real, 41.0);
    #0.875;
    scalar = 0;
    vector[32] = 1;
    control = 8'h48;
    #0.125;
    `checkd(scalar_time, 64'd2);
    `checkd(vector_time, 64'd3);
    `checkr(scalar_real, 2.0);
    `checkr(vector_real, 3.0);
    `checkd(combo_time, 64'd76);
    `checkr(combo_real, 76.0);
    $display("Event time checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
