// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

`timescale 1ns/1ps
module t;
  bit [31:0] checks = 0;

`ifdef GATE_INIT_TIMED
  logic [1:0] data2 = 2'b01;
  logic [6:0] data7 = 7'b1010101;
  logic [32:0] data33 = 33'h100000001;
  integer unsigned offset = 32'hffffffff;
  wire [1:0] selected2 = data2[offset +: 2];
  wire [2:0] selected7 = data7[offset +: 3];
  wire [1:0] selected33 = data33[offset +: 2];

  initial begin
    // This separate compilation checks the complete continuous producers.
    #1;
    `checkh(selected2, 2'bxx);
    `checkh(selected7, 3'bxxx);
    `checkh(selected33, 2'bxx);

    offset = 0;
    #1;
    `checkh(selected2, 2'b01);
    `checkh(selected7, 3'b101);
    `checkh(selected33, 2'b01);

    offset = 6;
    #1;
    `checkh(selected2, 2'bxx);
    `checkh(selected7, 3'bxx1);
    `checkh(selected33, 2'b00);

    offset = 31;
    #1;
    `checkh(selected2, 2'bxx);
    `checkh(selected7, 3'bxxx);
    `checkh(selected33, 2'b10);

    offset = 32;
    #1;
    `checkh(selected2, 2'bxx);
    `checkh(selected7, 3'bxxx);
    `checkh(selected33, 2'bx1);

    offset = 'x;
    #1;
    `checkh(selected2, 2'bxx);
    `checkh(selected7, 3'bxxx);
    `checkh(selected33, 2'bxx);

    offset = 'z;
    #1;
    `checkh(selected2, 2'bxx);
    `checkh(selected7, 3'bxxx);
    `checkh(selected33, 2'bxx);

    data2 = 2'b10;
    data7 = 7'b0101010;
    data33 = 33'h0ffffffff;
    offset = 0;
    #1;
    `checkh(selected2, 2'b10);
    `checkh(selected7, 3'b010);
    `checkh(selected33, 2'b11);

    $display("Four-state gate initialization timed checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
`else
  reg [1:0] data = 2'b01;
  integer unsigned offset = 32'hffffffff;
  wire [1:0] outside_expr = data[offset +: 2];

  initial begin
    // The net may still be X/Z before settling. A wrapped known bit is invalid.
    `checkh((outside_expr[1] === 1'b0) || (outside_expr[1] === 1'b1), 1'b0);
    `checkh((outside_expr[0] === 1'b0) || (outside_expr[0] === 1'b1), 1'b0);
    $display("Four-state gate initialization untimed checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
`endif
endmodule
