// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

// Independent behavioral model: no vendor primitive implementation is included.
module t;
  logic clk = 0;
  logic global_reset = 1;
  bit reset = 0;
  bit enable = 1;
  logic signed [17:0] a;
  logic signed [26:0] b;
  logic signed [47:0] c;
  bit [5:0] shift = 0;
  wire signed [47:0] p;

  always #5 clk = ~clk;
  initial #12 global_reset = 0;

  mac_pipeline model(clk, global_reset, reset, enable, a, b, c, shift, p);

  task automatic check_cycle(input logic [47:0] expected);
    @(posedge clk);
    #1;
    `checkh(p, expected);
    @(negedge clk);
  endtask

  initial begin
    a = 'x;
    b = 'x;
    c = 'x;
    check_cycle(48'd0);
    a = -18'sd3;
    b = 27'sd7;
    c = 48'sd5;
    check_cycle(-48'sd16);
    shift = 6'd2;
    check_cycle(-48'sd4);
    enable = 0;
    a = 'x;
    check_cycle(-48'sd4);
    enable = 1;
    check_cycle({48{1'bx}});
    reset = 1;
    check_cycle(48'd0);
    reset = 0;
    shift = 0;
    a = 18'sd123;
    b = -27'sd29;
    c = 48'sd11;
    check_cycle(-48'sd3556);
    b = 'z;
    check_cycle({48{1'bx}});
    global_reset = 1;
    #1;
    `checkh(p, 48'd0);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module mac_pipeline (
    input clk,
    input global_reset,
    input bit reset,
    input bit enable,
    input logic signed [17:0] a,
    input logic signed [26:0] b,
    input logic signed [47:0] c,
    input bit [5:0] shift,
    output logic signed [47:0] p
);
  always @(posedge clk or posedge global_reset) begin
    if (global_reset || reset) p <= 48'd0;
    else if (enable) p <= (a * b + c) >>> shift;
  end
endmodule
