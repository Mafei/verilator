// DESCRIPTION: Verilator: Repeat event controls capture counts, values and NBA targets
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
  logic [14:0] bank[3:1];
  logic [14:0] shadow[3:1];
  wire [14:0] bank1 = bank[1];
  wire [14:0] bank2 = bank[2];
  wire [14:0] bank3 = bank[3];
  wire [14:0] shadow1 = shadow[1];
  wire [14:0] shadow2 = shadow[2];
  wire [14:0] shadow3 = shadow[3];
  logic [6:0] zero_q = 0;
  logic [6:0] negative_q = 0;
  logic [6:0] wide_q = 0;
  logic [6:0] unsigned_q = 0;
  logic [6:0] blocking_bank[2:1];
  wire [6:0] blocking1 = blocking_bank[1];
  wire [6:0] blocking2 = blocking_bank[2];
  logic [6:0] blocking_rhs;
  logic [6:0] blocking_saved;
  int blocking_idx = 1;
  int blocking_count = 2;
  int blocking_count_calls = 0;
  int blocking_done = 0;
  int blocking_time = 0;
  int count_calls = 0;
  int rhs_calls = 0;
  int idx;
  int base;
  int round;
  int checks = 0;
  int ordinary_events = 0;
  logic [6:0] order_bank[2:1];
  int order_idx = 1;
  int order_count = 1;
  int order_rhs_calls = 0;
  int order_done = 0;
  event order_event;
  event update_a;
  event update_b;
`ifdef FOURSTATE_REPEAT
  logic [6:0] x_q = 0;
  logic [6:0] z_q = 0;
  int unknown_calls = 0;
  function automatic logic [6:0] unknown_count(input bit use_z);
    unknown_calls++;
    return use_z ? 7'bz000010 : 7'bx000001;
  endfunction
`endif

  function automatic int next_count(input int count);
    count_calls++;
    return count;
  endfunction

  function automatic logic [13:0] next_rhs(input int phase);
    rhs_calls++;
    case (phase)
      0: return 14'h154b;
      1: return 14'h2a35;
      default: return 14'h1e66;
    endcase
  endfunction

  function automatic int next_blocking_count;
    blocking_count_calls++;
    return blocking_count;
  endfunction

  // Saving the RHS must precede a repeat count that the RHS function changes.
  function automatic logic [6:0] order_rhs;
    order_rhs_calls++;
    order_count = 2;
`ifdef FOURSTATE_REPEAT
    return 7'bxz10z01;
`else
    return 7'h25;
`endif
  endfunction

  initial begin
    order_bank[1] = 0;
    order_bank[2] = 0;
    order_bank[order_idx] = repeat(order_count) @order_event order_rhs();
    order_done = 1;
  end

  initial begin
    #1;
    order_idx = 2;
    ->order_event;
    #0;
    `checkd(order_done, 0);
    #1;
    ->order_event;
    #0;
    `checkd(order_done, 1);
  end

  // Ordinary repeat statements still use their existing lowering.
  initial begin
    repeat(3) begin
      @(update_a or update_b);
      ordinary_events++;
    end
  end

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, bank1, bank2, bank3, shadow1, shadow2, shadow3,
              zero_q, negative_q, wide_q, unsigned_q, blocking1, blocking2);
    bank[1] = 0;
    bank[2] = 0;
    bank[3] = 0;
    shadow[1] = 0;
    shadow[2] = 0;
    shadow[3] = 0;
    blocking_bank[1] = 0;
    blocking_bank[2] = 0;
    zero_q <= repeat(0) @update_a 7'h2a;
    negative_q <= repeat(-3) @update_a 7'h35;
    // Bit 64 must survive; truncating this count to 64 bits would commit too soon.
    wide_q <= repeat(65'h1_0000_0000_0000_0001) @update_a 7'h55;
    unsigned_q <= repeat(32'h8000_0001) @update_a 7'h66;
`ifdef FOURSTATE_REPEAT
    x_q <= repeat(unknown_count(0)) @update_a 7'h4b;
    z_q <= repeat(unknown_count(1)) @update_a 7'h66;
    `checkh(x_q, 7'b0);
    `checkh(z_q, 7'b0);
`endif
    `checkh(zero_q, 7'b0);
    `checkh(negative_q, 7'b0);
    for (round = 0; round < 3; round++) begin
      idx = round + 1;
      base = round + 1;
      {bank[idx][base+:7], shadow[idx][base+:7]}
          <= repeat(next_count(round + 1)) @(update_a or update_b) next_rhs(round);
    end
    idx = 1;
    base = 7;
    round = 9;
    #0;
    `checkh(zero_q, 7'b0);
    `checkh(negative_q, 7'b0);
`ifdef FOURSTATE_REPEAT
    `checkh(x_q, 7'b0);
    `checkh(z_q, 7'b0);
`endif
    #1;
    `checkh(zero_q, 7'h2a);
    `checkh(negative_q, 7'h35);
`ifdef FOURSTATE_REPEAT
    `checkh(x_q, 7'h4b);
    `checkh(z_q, 7'h66);
    `checkd(unknown_calls, 2);
`endif
    `checkd(count_calls, 3);
    `checkd(rhs_calls, 3);
    `checkh(bank[1], 15'b0);
    `checkh(bank[2], 15'b0);
    `checkh(bank[3], 15'b0);
    `checkh(shadow[1], 15'b0);
    `checkh(shadow[2], 15'b0);
    `checkh(shadow[3], 15'b0);
    ->update_a;
    `checkh(bank[1], 15'b0);
    `checkh(bank[2], 15'b0);
    `checkh(bank[3], 15'b0);
    `checkh(shadow[1], 15'b0);
    `checkh(shadow[2], 15'b0);
    `checkh(shadow[3], 15'b0);
    #0;
    `checkh(bank[1], 15'b0);
    `checkh(bank[2], 15'b0);
    `checkh(bank[3], 15'b0);
    `checkh(shadow[1], 15'b0);
    `checkh(shadow[2], 15'b0);
    `checkh(shadow[3], 15'b0);
    $strobe("REPEAT STROBE event=1 t=%0t bank1=%h bank2=%h bank3=%h shadow1=%h shadow2=%h shadow3=%h",
            $time, bank1, bank2, bank3, shadow1, shadow2, shadow3);
    #1;
    `checkh(bank[1], 15'h0054);
    `checkh(bank[2], 15'b0);
    `checkh(bank[3], 15'b0);
    `checkh(shadow[1], 15'h0096);
    `checkh(shadow[2], 15'b0);
    `checkh(shadow[3], 15'b0);
    ->update_b;
    `checkh(bank[2], 15'b0);
    `checkh(bank[3], 15'b0);
    `checkh(shadow[2], 15'b0);
    `checkh(shadow[3], 15'b0);
    #0;
    `checkh(bank[2], 15'b0);
    `checkh(bank[3], 15'b0);
    `checkh(shadow[2], 15'b0);
    `checkh(shadow[3], 15'b0);
    $strobe("REPEAT STROBE event=2 t=%0t bank1=%h bank2=%h bank3=%h shadow1=%h shadow2=%h shadow3=%h",
            $time, bank1, bank2, bank3, shadow1, shadow2, shadow3);
    #1;
    `checkh(bank[1], 15'h0054);
    `checkh(bank[2], 15'h0150);
    `checkh(bank[3], 15'b0);
    `checkh(shadow[1], 15'h0096);
    `checkh(shadow[2], 15'h00d4);
    `checkh(shadow[3], 15'b0);
    ->update_a;
    `checkh(bank[3], 15'b0);
    `checkh(shadow[3], 15'b0);
    #0;
    `checkh(bank[3], 15'b0);
    `checkh(shadow[3], 15'b0);
    $strobe("REPEAT STROBE event=3 t=%0t bank1=%h bank2=%h bank3=%h shadow1=%h shadow2=%h shadow3=%h",
            $time, bank1, bank2, bank3, shadow1, shadow2, shadow3);
    #1;
    `checkh(bank[1], 15'h0054);
    `checkh(bank[2], 15'h0150);
    `checkh(bank[3], 15'h01e0);
    `checkh(shadow[1], 15'h0096);
    `checkh(shadow[2], 15'h00d4);
    `checkh(shadow[3], 15'h0330);
    `checkh(wide_q, 7'b0);
    `checkh(unsigned_q, 7'b0);
    `checkd(ordinary_events, 3);
    `checkh(order_bank[1], 7'b0);
`ifdef FOURSTATE_REPEAT
    `checkh(order_bank[2], 7'bxz10z01);
`else
    `checkh(order_bank[2], 7'h25);
`endif
    `checkd(order_rhs_calls, 1);
    `checkd(order_count, 2);
`ifdef FOURSTATE_REPEAT
    blocking_rhs = 7'bxz10z01;
`else
    blocking_rhs = 7'h25;
`endif
    blocking_saved = blocking_rhs;
    fork
      begin
        blocking_bank[blocking_idx] = repeat(next_blocking_count()) @update_b blocking_rhs;
        blocking_time = int'($time);
        blocking_done = 1;
      end
      begin
        #1;
        blocking_idx = 2;
        blocking_rhs = 0;
        blocking_count = 0;
        ->update_b;
        #0;
        `checkd(blocking_done, 0);
        #1;
        `checkd(blocking_done, 0);
        ->update_b;
        #0;
        `checkd(blocking_done, 1);
        `checkd(blocking_time, 6);
      end
    join
    `checkh(blocking_bank[1], 7'b0);
    `checkh(blocking_bank[2], blocking_saved);
    `checkd(blocking_count_calls, 1);
    `checkd(blocking_done, 1);
    $display("Repeat NBA checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
