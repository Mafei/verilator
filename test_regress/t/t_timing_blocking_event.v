// DESCRIPTION: Verilator: Blocking intra-assignment events snapshot once and wait once
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
  bit [31:0] checks = 0;
  wire [3:0] done;
  blocking_event_width #(7) w7 (done[0]);
  blocking_event_width #(31) w31 (done[1]);
  blocking_event_width #(65) w65 (done[2]);
  blocking_event_width #(95) w95 (done[3]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #20;
    `checkh(done, 4'b1111);
    $display("Blocking event checks: %0d", w7.checks + w31.checks + w65.checks + w95.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module blocking_event_width #(
    parameter int WIDTH = 7
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  logic [WIDTH-1:0] source = '0;
  logic [WIDTH-1:0] whole = '0;
  logic [WIDTH+1:0] bank[3:1];
  logic [8:0] tail = '0;
  logic [WIDTH-1:0] delayed = '0;
  logic [WIDTH-1:0] queued[3:1];
  wire [WIDTH-1:0] whole_view = whole;
  wire [WIDTH+1:0] bank1_view = bank[1];
  wire [WIDTH+1:0] bank2_view = bank[2];
  wire [WIDTH-1:0] delayed_view = delayed;
  wire [WIDTH-1:0] queued1_view = queued[1];
  wire [WIDTH-1:0] queued2_view = queued[2];
  wire [WIDTH-1:0] queued3_view = queued[3];
  int rhs_calls = 0;
  int index_calls = 0;
  int whole_done = 0;
  int concat_done = 0;
  int delay_done = 0;
  int slot = 1;
  int base = 0;
  event update;

  function automatic logic [WIDTH-1:0] pattern(input int seed);
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      case ((bitno + seed) % 4)
        0: pattern[bitno] = 1'b0;
        1: pattern[bitno] = 1'b1;
`ifdef BLOCKING_EVENT_FOURSTATE
        2: pattern[bitno] = 1'bx;
        3: pattern[bitno] = 1'bz;
`else
        2: pattern[bitno] = 1'b1;
        3: pattern[bitno] = 1'b0;
`endif
      endcase
    end
  endfunction
  function automatic logic [WIDTH-1:0] snapshot(input logic [WIDTH-1:0] value);
    rhs_calls++;
    return value;
  endfunction
  function automatic int target();
    index_calls++;
    return slot;
  endfunction
  task automatic concat_wait;
    {bank[target()][base+:WIDTH], tail[base+:7]} = @update{snapshot(source), 7'b1010101};
    concat_done++;
  endtask

  initial begin
    for (int index = 1; index <= 3; index++) begin
      bank[index] = '0;
      queued[index] = '0;
    end
    source = pattern(0);
    #1;
    whole = @update snapshot(source);
    whole_done++;
    `checkd($time, 3);
    `checkh(whole, pattern(0));
    concat_wait();
    `checkd($time, 6);
    `checkh(bank[2], {1'b0, pattern(1), 1'b0});
    `checkh(tail, 9'b010101010);
    delayed = #3 snapshot(source);
    delay_done++;
    `checkd($time, 9);
    `checkh(delayed, pattern(2));
  end
  initial begin
    #2;
    `checkd(rhs_calls, 1);
    `checkd(whole_done, 0);
    `checkh(whole, '0);
    source = pattern(1);
    #1;
    ->update;
    #1;
    `checkd(whole_done, 1);
    `checkd(rhs_calls, 2);
    `checkd(index_calls, 0);
    source = pattern(2);
    slot = 2;
    base = 1;
    #2;
    ->update;
    #1;
    `checkd(concat_done, 1);
    `checkd(rhs_calls, 3);
    `checkd(index_calls, 1);
    `checkh(bank[1], '0);
    `checkh(bank[3], '0);
    source = pattern(3);
    slot = 1;
    base = 2;
    #3;
    `checkd(delay_done, 1);
    `checkd(index_calls, 1);
    `checkh(delayed, pattern(2));
    // Repeated event-controlled NBAs capture each RHS and side-effecting target now.
    for (int index = 1; index <= 3; index++) begin
      slot = index;
      queued[target()] <= @update snapshot(pattern(index));
    end
    `checkd(index_calls, 4);
    `checkd(rhs_calls, 6);
    slot = 1;
    source = '0;
    #1;
    ->update;
    #1;
    `checkh(queued[1], pattern(1));
    `checkh(queued[2], pattern(2));
    `checkh(queued[3], pattern(3));
    `checkd(index_calls, 4);
    `checkd(rhs_calls, 6);
    done = 1;
  end
endmodule
