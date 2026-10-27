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
  bit clk = 0;
  logic [1:0] qualifiers [0:2];
  logic [1:0] index = 0;
  int unsigned hits = 0;
  int unsigned unknown_hits = 0;
  int unsigned edges = 0;
  int unsigned expected_hits = 0;
  int unsigned expected_unknowns = 0;
  int unsigned checks = 0;

`ifdef IFF_EXPLICIT_CONTROL
  // An independent reference form for simulators without native iff parsing.
  always @(posedge clk) if (qualifiers[index]) hits++;
  always @(posedge clk) if ($isunknown(qualifiers[index])) unknown_hits++;
`else
  always @(posedge clk iff qualifiers[index]) hits++;
  always @(posedge clk iff $isunknown(qualifiers[index])) unknown_hits++;
`endif
  always @(posedge clk) edges++;

  function automatic logic [1:0] qualifier(input int phase);
    case (phase)
      0: return 2'b00;
      1: return 2'b01;
      2: return 2'b10;
      3: return 2'b11;
      4: return 2'b0x;
      5: return 2'bx0;
      6: return 2'b1x;
      7: return 2'bx1;
      8: return 2'b0z;
      9: return 2'bz0;
      10: return 2'b1z;
      default: return 2'bz1;
    endcase
  endfunction

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, clk, hits, unknown_hits, edges);
    qualifiers[0] = 0;
    qualifiers[1] = 0;
    qualifiers[2] = 0;
    for (int phase = 0; phase < 12; phase++) begin
      index = 2'(phase % 3);
      qualifiers[index] = qualifier(phase);
      case (phase)
        1, 2, 3, 6, 7, 10, 11: expected_hits++;
        default: begin end
      endcase
      if (phase >= 4) expected_unknowns++;
      #1;
      clk = 1;
      #1;
      `checkd(hits, expected_hits);
      `checkd(unknown_hits, expected_unknowns);
      `checkd(edges, 32'(phase + 1));
      clk = 0;
    end
    $display("Sensitivity iff checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
