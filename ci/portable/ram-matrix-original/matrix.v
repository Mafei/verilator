// DESCRIPTION: Verilator: Four-state array snapshots across split C functions
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b exp=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

`timescale 1ps/1ps
module array_tmp_lane #(
  parameter int WIDTH = 7,
  parameter int LO = 1,
  parameter bit UP = 0,
  parameter bit PACKUP = 0,
  parameter int HI = LO + 2
)(output bit done);
  // Both packed orderings are intentional regression inputs.
  /* verilator lint_off ASCRANGE */
  typedef logic [PACKUP ? 0 : WIDTH - 1 : PACKUP ? WIDTH - 1 : 0] word_t;
  /* verilator lint_on ASCRANGE */
  localparam word_t ZERO = '0;
  localparam word_t ONES = '1;
  localparam word_t ALLX = 'x;
  localparam word_t ALLZ = 'z;
  localparam word_t MIXED = word_t'(6'b10xz01);
  localparam word_t FIRST = 'h11;
  localparam word_t MIDDLE = 'h22;
  localparam word_t LAST = 'h33;
  word_t bank[UP ? LO : HI : UP ? HI : LO];
  wire [WIDTH - 1:0] first_word = bank[LO];
  wire [WIDTH - 1:0] middle_word = bank[LO + 1];
  wire [WIDTH - 1:0] last_word = bank[HI];
  word_t rhs;
  int index;
  logic signed [31:0] invalid_index;
  int side_effects;
  int phase;
  int checks;
  event update;

  function automatic word_t rhs_step();
    side_effects++;
    return ONES;
  endfunction

  function automatic int next_index();
    side_effects++;
    return LO;
  endfunction

  task automatic report(input int current_phase);
    phase = current_phase;
    $display("ARRAY_TMP W=%0d UP=%0d PACKUP=%0d phase=%0d first=%b middle=%b last=%b side=%0d checks=%0d",
             WIDTH, UP, PACKUP, phase, bank[LO], bank[LO + 1], bank[HI], side_effects, checks);
  endtask

  initial begin
    done = 0;
    side_effects = 0;
    checks = 0;
    // The original reproducer has no event or non-blocking assignment.
    bank[LO] = FIRST;
    bank[LO + 1] = MIDDLE;
    bank[HI] = LAST;
    #1;
    `checkh(bank[LO], FIRST);
    `checkh(bank[LO + 1], MIDDLE);
    `checkh(bank[HI], LAST);
    report(0);

    index = LO;
    bank[index] = ALLX;
    index = LO + 1;
    bank[index] = ALLZ;
    index = HI;
    bank[index] = ONES;
    index = LO;
    #1;
    `checkh(bank[LO], ALLX);
    `checkh(bank[LO + 1], ALLZ);
    `checkh(bank[HI], ONES);
    report(1);

    foreach (bank[i]) bank[i] = ZERO;
    rhs = MIXED;
    index = LO;
    bank[index] <= rhs;
    index = HI;
    rhs = ZERO;
    #1;
    `checkh(bank[LO], MIXED);
    `checkh(bank[LO + 1], ZERO);
    `checkh(bank[HI], ZERO);
    report(2);

    foreach (bank[i]) bank[i] = ZERO;
    rhs = ALLZ;
    index = LO + 1;
    bank[index] <= @(update) rhs;
    index = HI;
    rhs = ALLX;
    #1;
    `checkh(bank[LO], ZERO);
    `checkh(bank[LO + 1], ZERO);
    `checkh(bank[HI], ZERO);
    report(3);
    -> update;
    #1;
    `checkh(bank[LO], ZERO);
    `checkh(bank[LO + 1], ALLZ);
    `checkh(bank[HI], ZERO);
    report(4);

    foreach (bank[i]) bank[i] = ZERO;
    side_effects = 0;
    invalid_index = 'x;
    bank[invalid_index] = rhs_step();
    invalid_index = 'z;
    bank[invalid_index] = rhs_step();
    invalid_index = LO - 1;
    bank[invalid_index] = rhs_step();
    invalid_index = HI + 1;
    bank[invalid_index] = rhs_step();
    #1;
    `checkh(side_effects, 4);
    foreach (bank[i]) `checkh(bank[i], ZERO);
    report(5);

    side_effects = 0;
    invalid_index = 'x;
    bank[invalid_index] <= rhs_step();
    invalid_index = 'z;
    bank[invalid_index] <= rhs_step();
    invalid_index = LO - 1;
    bank[invalid_index] <= rhs_step();
    invalid_index = HI + 1;
    bank[invalid_index] <= rhs_step();
    #1;
    `checkh(side_effects, 4);
    foreach (bank[i]) `checkh(bank[i], ZERO);
    report(6);

    side_effects = 0;
    invalid_index = 'x;
    bank[invalid_index] <= @(update) rhs_step();
    invalid_index = 'z;
    bank[invalid_index] <= @(update) rhs_step();
    invalid_index = LO - 1;
    bank[invalid_index] <= @(update) rhs_step();
    invalid_index = HI + 1;
    bank[invalid_index] <= @(update) rhs_step();
    #1;
    `checkh(side_effects, 4);
    foreach (bank[i]) `checkh(bank[i], ZERO);
    report(7);
    -> update;
    #1;
    `checkh(side_effects, 4);
    foreach (bank[i]) `checkh(bank[i], ZERO);
    report(8);

    bank[LO] <= @(update) ALLX;
    bank[LO + 1] <= @(update) ALLZ;
    bank[HI] <= @(update) MIXED;
    #1;
    -> update;
    #1;
    `checkh(bank[LO], ALLX);
    `checkh(bank[LO + 1], ALLZ);
    `checkh(bank[HI], MIXED);
    report(9);

    foreach (bank[i]) bank[i] = ZERO;
    side_effects = 0;
    bank[next_index()] = MIXED;
    #1;
    `checkh(side_effects, 1);
    `checkh(bank[LO], MIXED);
    `checkh(bank[LO + 1], ZERO);
    `checkh(bank[HI], ZERO);
    report(10);

    bank[LO] = ZERO;
    side_effects = 0;
    rhs = ALLZ;
    bank[next_index()] <= rhs;
    rhs = ALLX;
    #1;
    `checkh(side_effects, 1);
    `checkh(bank[LO], ALLZ);
    `checkh(bank[LO + 1], ZERO);
    `checkh(bank[HI], ZERO);
    report(11);

    bank[LO] = ZERO;
    side_effects = 0;
    rhs = MIXED;
    bank[next_index()] <= @(update) rhs;
    rhs = ALLX;
    #1;
    `checkh(side_effects, 1);
    `checkh(bank[LO], ZERO);
    -> update;
    #1;
    `checkh(side_effects, 1);
    `checkh(bank[LO], MIXED);
    `checkh(bank[LO + 1], ZERO);
    `checkh(bank[HI], ZERO);
    report(12);

    invalid_index = 'x;
    `checkh(bank[invalid_index], ALLX);
    invalid_index = 'z;
    `checkh(bank[invalid_index], ALLX);
    invalid_index = LO - 1;
    `checkh(bank[invalid_index], ALLX);
    invalid_index = HI + 1;
    `checkh(bank[invalid_index], ALLX);
    `checkh(checks, 53);
    report(13);
    done = 1;
  end
endmodule

module t;
  bit [5:0] done;
  array_tmp_lane #(7, 1, 0, 0) u7d(done[0]);
  array_tmp_lane #(7, 1, 1, 1) u7a(done[1]);
  array_tmp_lane #(33, -2, 0, 0) u33d(done[2]);
  array_tmp_lane #(33, -2, 1, 1) u33a(done[3]);
  array_tmp_lane #(65, 3, 0, 0) u65d(done[4]);
  array_tmp_lane #(65, 3, 1, 1) u65a(done[5]);
  initial begin
    $dumpfile("t_fourstate_array_tmp.vcd");
    $dumpvars(0, t);
    wait (&done);
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
