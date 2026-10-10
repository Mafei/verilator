// DESCRIPTION: Verilator: Capture event-controlled NBA concat values and targets
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  logic [64:0] bank[3:1];
  logic [32:0] a33 = '0;
  logic [64:0] b65 = '0;
  logic [1:33] asc = '0;
  logic [64:0] plain = '0;
  wire [64:0] bank1_view = bank[1];
  wire [64:0] bank2_view = bank[2];
  logic [64:0] rhs;
  logic [32:0] rhs_asc;
  logic [64:0] saved_rhs;
  logic [32:0] saved_asc;
  logic [64:0] old_bank1;
  logic [64:0] old_bank2;
  logic [32:0] old_a33;
  logic [64:0] old_b65;
  logic [1:33] old_asc;
  logic [64:0] old_plain;
  logic [64:0] expected_bank1;
  logic [64:0] expected_bank2;
  logic [32:0] expected_a33;
  logic [64:0] expected_b65;
  int idx = 1;
  int base = 1;
  int round;
  int checks = 0;
  event update;

  function automatic logic [64:0] payload(input int phase);
    for (int bitno = 0; bitno < 65; bitno++) begin
      case ((bitno + phase) % 4)
        0: payload[bitno] = 1'b0;
        1: payload[bitno] = 1'b1;
`ifdef NBA_EVENT_FOURSTATE
        2: payload[bitno] = 1'bx;
        3: payload[bitno] = 1'bz;
`else
        2: payload[bitno] = 1'b1;
        3: payload[bitno] = 1'b0;
`endif
      endcase
    end
  endfunction

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, bank1_view, bank2_view, a33, b65, asc, plain);
    bank[1] = '0;
    bank[2] = '0;
    bank[3] = '0;
    for (round = 0; round < 4; round++) begin
      #1;
      rhs = payload(round);
      rhs_asc = 33'(payload(round + 1));
      saved_rhs = rhs;
      saved_asc = rhs_asc;
      idx = 1;
      base = 1;
      old_bank1 = bank[1];
      old_bank2 = bank[2];
      old_a33 = a33;
      old_b65 = b65;
      old_asc = asc;
      old_plain = plain;
      expected_bank1 = old_bank1;
      expected_bank2 = old_bank2;
      expected_a33 = old_a33;
      expected_b65 = old_b65;
      expected_bank2[1+:33] = saved_rhs[64:32];
      expected_bank1[1+:7] = saved_rhs[31:25];
      expected_a33[1+:15] = saved_rhs[24:10];
      expected_b65[1+:10] = saved_rhs[9:0];
      {bank[idx+1][base+:33], bank[idx][base+:7], a33[base+:15], b65[base+:10]} <= @update rhs;
      asc <= @update rhs_asc;
      // Pending writes retain the original values and target indices.
      rhs = payload(round + 2);
      rhs_asc = 33'(payload(round + 3));
      idx = 3;
      base = 20;
      #1;
      `checkd($time, 64'(3 * round + 2));
      `checkh(bank[1], old_bank1);
      `checkh(bank[2], old_bank2);
      `checkh(a33, old_a33);
      `checkh(b65, old_b65);
      `checkh(asc, old_asc);
      `checkh(plain, old_plain);
      ->update;
      plain <= saved_rhs;
      // The triggering caller has not yielded to scheduled NBA updates.
      `checkd($time, 64'(3 * round + 2));
      `checkh(bank[1], old_bank1);
      `checkh(bank[2], old_bank2);
      `checkh(a33, old_a33);
      `checkh(b65, old_b65);
      `checkh(asc, old_asc);
      `checkh(plain, old_plain);
      #0;
      // A module #0 continuation runs in Inactive, before NBA updates.
      `checkd($time, 64'(3 * round + 2));
      `checkh(bank[1], old_bank1);
      `checkh(bank[2], old_bank2);
      `checkh(a33, old_a33);
      `checkh(b65, old_b65);
      `checkh(asc, old_asc);
      `checkh(plain, old_plain);
      // The driver checks this observation separately from physical-time VCD.
      $strobe("NBA STROBE round=%0d t=%0t bank1=%b bank2=%b a33=%b b65=%b asc=%b plain=%b", round,
              $time, bank[1], bank[2], a33, b65, asc, plain);
      #1;
      `checkd($time, 64'(3 * round + 3));
      `checkh(bank[1], expected_bank1);
      `checkh(bank[2], expected_bank2);
      `checkh(a33, expected_a33);
      `checkh(b65, expected_b65);
      `checkh(asc, saved_asc);
      `checkh(plain, saved_rhs);
      `checkh(bank[3], 65'b0);
    end
    $display("Event NBA checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
