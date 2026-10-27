// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define compare_known(valuev,knownv,equalv) begin `checkh((valuev) === (knownv), 1'(equalv)); `checkh((knownv) === (valuev), 1'(equalv)); `checkh((valuev) !== (knownv), 1'(!(equalv))); `checkh((knownv) !== (valuev), 1'(!(equalv))); end
// verilog_format: on

module t;
  logic [6:0] value7;
  logic [94:0] value95;
  bit [6:0] known7;
  bit [94:0] known95;
  int unsigned checks = 0;
  int position95;
  int position7;

  initial begin
    for (int phase = 0; phase < 6; phase++) begin
      case (phase)
        0: position95 = 1;
        1: position95 = 2;
        2: position95 = 31;
        3: position95 = 32;
        4: position95 = 64;
        default: position95 = 94;
      endcase
      position7 = phase + 1;
      known7 = '1;
      known95 = '1;
      value7 = known7;
      value95 = known95;
      #1;
      `compare_known(value7, known7, 1);
      `compare_known(value95, known95, 1);
      value7[position7] = 1'bx;
      value95[position95] = 1'bx;
      #1;
      `compare_known(value7, known7, 0);
      `compare_known(value95, known95, 0);
      value7[position7] = 1'bz;
      value95[position95] = 1'bz;
      #1;
      `compare_known(value7, known7, 0);
      `compare_known(value95, known95, 0);
    end
    $display("Known-operand case equality checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
