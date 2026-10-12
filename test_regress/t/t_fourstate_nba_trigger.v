// DESCRIPTION: Nonblocking event-array trigger target index snapshots
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps/1ps
// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on
module t;
  event updates[3:1];
  int count1 = 0;
  int count2 = 0;
  int count3 = 0;
  int index;
  int checks = 0;
  int phase;
  always @(updates[1]) count1++;
  always @(updates[2]) count2++;
  always @(updates[3]) count3++;
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, count1, count2, count3);
    for (phase = 0; phase < 4; phase++) begin
      #1;
      for (index = 1; index <= 3; index++) begin
        ->>updates[index];
      end
      index = 1;
      `checkh(count1, phase);
      `checkh(count2, phase);
      `checkh(count3, phase);
      #1;
      `checkh(count1, phase + 1);
      `checkh(count2, phase + 1);
      `checkh(count3, phase + 1);
      $display("TRIGGER_FINAL phase=%0d counts=%0d,%0d,%0d", phase, count1, count2, count3);
    end
    $display("EVENT_NBA_TRIGGER_PASS checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
