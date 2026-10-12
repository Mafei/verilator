// DESCRIPTION: Independent event-controlled NBA scheduling and capture controls
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps/1ps
// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on
module t;
  event update;
  event counted;
  logic [32:0] bank[3:1];
  logic [32:0] hi[3:1];
  logic [31:0] lo[3:1];
  wire [32:0] bank1 = bank[1];
  wire [32:0] bank2 = bank[2];
  wire [32:0] bank3 = bank[3];
  wire [32:0] hi1 = hi[1];
  wire [32:0] hi2 = hi[2];
  wire [32:0] hi3 = hi[3];
  wire [31:0] lo1 = lo[1];
  wire [31:0] lo2 = lo[2];
  wire [31:0] lo3 = lo[3];
  logic [64:0] rhs;
  logic [32:0] partial = '0;
  logic [1:33] ascending = '0;
  logic [32:0] repeated = '0;
  logic [32:0] rearmed = '0;
  logic [32:0] expected[3:1];
  logic [64:0] expected_wide[3:1];
  logic [32:0] expected_partial;
  logic [32:0] expected_ascending;
  int index;
  int base;
  int repeat_count;
  int checks = 0;
  int phase;
  int slot;

  function automatic logic [64:0] payload(input int value);
    for (int bitno = 0; bitno < 65; bitno++) begin
      case ((value + bitno) % 4)
        0: payload[bitno] = 1'b0;
        1: payload[bitno] = 1'b1;
        2: payload[bitno] = 1'bx;
        3: payload[bitno] = 1'bz;
      endcase
    end
  endfunction

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, bank1, bank2, bank3, hi1, hi2, hi3, lo1, lo2, lo3,
              partial, ascending, repeated, rearmed);
    foreach (bank[slot]) begin
      bank[slot] = '0;
      hi[slot] = '0;
      lo[slot] = '0;
    end
    for (phase = 0; phase < 4; phase++) begin
      // Several invocations of the same syntactic NBA statement remain armed
      // concurrently. Each needs its own RHS and target-index snapshot.
      for (slot = 1; slot <= 3; slot++) begin
        index = slot;
        rhs = payload(phase + slot);
        expected[index] = 33'(rhs);
        expected_wide[index] = rhs;
        bank[index] <= @update 33'(rhs);
        {hi[index], lo[index]} <= @update rhs;
      end
      rhs = payload(phase + 1);
      base = 3;
      expected_partial = partial;
      expected_partial[3+:15] = rhs[14:0];
      expected_ascending = 33'(rhs);
      partial[base+:15] <= @update rhs[14:0];
      ascending <= @update 33'(rhs);
      // Later mutations must not change any pending assignment.
      rhs = payload(phase + 3);
      index = 3;
      base = 18;
      #1;
      $display("ARM phase=%0d t=%0t bank1=%b partial=%b", phase, $time, bank1, partial);
      ->update;
      // A triggering process has not yielded to NBA execution yet.
      $display("ACTIVE phase=%0d t=%0t bank1=%b partial=%b", phase, $time, bank1, partial);
      $strobe("POST phase=%0d t=%0t bank1=%b partial=%b", phase, $time, bank1, partial);
      #1;
      for (slot = 1; slot <= 3; slot++) begin
        `checkh(bank[slot], expected[slot]);
        `checkh({hi[slot], lo[slot]}, expected_wide[slot]);
      end
      `checkh(partial, expected_partial);
      `checkh(ascending, expected_ascending);
      $display("FINAL phase=%0d t=%0t bank1=%b partial=%b", phase, $time, bank1, partial);
    end
    // A fresh wait is armed only for the next trigger; repeated trigger before
    // re-arming cannot cause an extra write.
    for (phase = 0; phase < 3; phase++) begin
      rhs = payload(phase);
      rearmed <= @update 33'(rhs);
      rhs = payload(phase + 2);
      #1;
      ->update;
      #1;
      `checkh(rearmed, 33'(payload(phase)));
      ->update;
      #1;
      `checkh(rearmed, 33'(payload(phase)));
    end
    $display("EVENT_NBA_CONTROLS_PASS checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
