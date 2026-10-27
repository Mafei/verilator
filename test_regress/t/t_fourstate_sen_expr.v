// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  logic [6:0] body [0:2];
  logic [1:0] readptr = 0;
  logic gate = 0;
  bit armed = 0;
  bit [31:0] checks = 0;
  bit [31:0] direct_hits = 0, equal_hits = 0, unknown_hits = 0;
  bit [31:0] conditional_hits = 0, rises = 0, falls = 0;
  logic [6:0] direct_value = 0, conditional_value = 0;
  bit [31:0] conditional_before;

  always @(readptr or body[readptr]) begin
    if (armed) begin
      direct_hits++;
      direct_value = body[readptr];
    end
  end
  // Two-state results can still require captures for their four-state operands.
  always @(body[readptr] === 7'h12) if (armed) equal_hits++;
  always @($isunknown(body[readptr])) if (armed) unknown_hits++;
  always @(gate ? body[readptr] : body[0]) begin
    if (armed) begin
      conditional_hits++;
      conditional_value = gate ? body[readptr] : body[0];
    end
  end
  always @(posedge body[readptr]) if (armed) rises++;
  always @(negedge body[readptr]) if (armed) falls++;

  task automatic check_direct(input bit [31:0] hits, input logic [6:0] value,
                              input bit [31:0] equals, input bit [31:0] unknowns);
    `checkd(direct_hits, hits);
    `checkh(direct_value, value);
    `checkd(equal_hits, equals);
    `checkd(unknown_hits, unknowns);
  endtask

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, direct_value, conditional_value, readptr, gate);
    body[0] = 7'h11;
    body[1] = 7'h22;
    body[2] = 7'h33;
    #1;
    armed = 1;
    check_direct(0, 0, 0, 0);
    body[1] = 7'h24;
    #1;
    check_direct(0, 0, 0, 0);
    body[0] = 7'h12;
    #1;
    check_direct(1, 7'h12, 1, 0);
    body[0] = 7'b00x0010;
    #1;
    check_direct(2, 7'b00x0010, 2, 1);
    body[0] = 7'b00z0010;
    #1;
    check_direct(3, 7'b00z0010, 2, 1);
    readptr = 1;
    #1;
    check_direct(4, 7'h24, 2, 2);
    readptr = 3;
    #1;
    check_direct(5, 'x, 2, 3);
    readptr = 3;
    #1;
    check_direct(5, 'x, 2, 3);
    readptr = 2'bx1;
    #1;
    check_direct(6, 'x, 2, 3);
    readptr = 2'bz1;
    #1;
    check_direct(7, 'x, 2, 3);
    readptr = 2;
    #1;
    check_direct(8, 7'h33, 2, 4);
    body[2] = 7'h34;
    #1;
    check_direct(9, 7'h34, 2, 4);
    `checkd(rises, 2);
    `checkd(falls, 2);

    conditional_before = conditional_hits;
    `checkh(conditional_value, 7'b00z0010);
    gate = 1;
    #1;
    `checkd(conditional_hits, conditional_before + 1);
    `checkh(conditional_value, 7'h34);
    body[0] = 7'h15;
    #1;
    `checkd(conditional_hits, conditional_before + 1);
    `checkh(conditional_value, 7'h34);
    body[2] = 7'h36;
    #1;
    `checkd(conditional_hits, conditional_before + 2);
    `checkh(conditional_value, 7'h36);
    gate = 1'bx;
    #1;
    `checkd(conditional_hits, conditional_before + 3);
    `checkh(conditional_value, 7'b0x101xx);
    gate = 1'bz;
    #1;
    `checkd(conditional_hits, conditional_before + 3);
    `checkh(conditional_value, 7'b0x101xx);
    $display("Sensitivity expression checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
