// DESCRIPTION: Verilator: Complete clocked value/XZ traces through an MT exec graph
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b exp=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0)
// verilog_format: on

`timescale 1ps/1ps
module t(input bit clk);
  logic [32:0] sample = '0;
  int phase = 0;

  function automatic logic [32:0] pattern(input int index);
    case (index)
      0, 5: return '1;
`ifdef FOURSTATE
      1: return 'x;
      2: return 'z;
      3: return 33'(6'b10xz01);
`else
      1, 2: return '0;
      3: return 33'(6'b100001);
`endif
      default: return '0;
    endcase
  endfunction

  always @(posedge clk) begin
    `checkh(sample, phase == 0 ? 33'b0 : pattern(phase - 1));
    $display("MT_TRACE phase=%0d observed=%b", phase, sample);
    sample <= pattern(phase);
    phase <= phase + 1;
  end

  final begin
    `checkh(phase, 6);
    `checkh(sample, 33'h1ffffffff);
    $display("MT_FINAL phase=%0d sample=%b", phase, sample);
  end
endmodule
