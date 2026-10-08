// DESCRIPTION: Verilator: Wake dependent logic after Inactive #0 resumptions
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
  logic [6:0] source7 = 0;
  logic [32:0] source33 = 0;
  logic [64:0] source65 = 0;
  logic [32:0] scheduled33 = 0;
  wire [6:0] decoded7 = source7[1] ? 7'h55 : 7'h00;
  wire [32:0] rotated33 = {source33[31:0], source33[32]};
  wire [64:0] rotated65 = {source65[63:0], source65[64]};
  int unsigned decoded_events = 0;
  int unsigned before_events;
  int unsigned delay_ticks;
`ifdef ZERO_XZ
  localparam logic [32:0] MIXED33 = {1'bz, 28'h1234567, 4'b10xz};
  localparam logic [64:0] MIXED65 = {1'bx, 60'h123456789abcdef, 4'b01zx};
`else
  localparam logic [32:0] MIXED33 = {1'b1, 28'h1234567, 4'b1010};
  localparam logic [64:0] MIXED65 = {1'b0, 60'h123456789abcdef, 4'b0101};
`endif

  always @(decoded7)++decoded_events;

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    // Each second #0 samples after the preceding Inactive writes and the
    // resulting Active work, without advancing simulation time.
    #0 source7 = 2;
    source33 = 33'h123456789;
    source65 = 65'h123456789abcdef01;
    #0;
    `checkh(decoded7, 7'h55)
    `checkh(rotated33, 33'h468acf13)
    `checkh(rotated65, 65'h468acf13579bde03)
    #0 source7 = 0;
    #0;
    `checkh(decoded7, 7'h00)
    #0 source7 = 2;
    #0 scheduled33 <= source33;
    // Inactive is exhausted before NBA. Check at the next physical time so
    // the queue must have committed in the previous time slot.
    #1;
    `checkh(decoded7, 7'h55)
    `checkh(scheduled33, 33'h123456789)

    for (int phase = 0; phase < 6; ++phase) begin
      delay_ticks = phase[0] ? 2 : 0;
      #(delay_ticks);
      source7 = 7'(phase);
      source33 = {phase[0], 28'h7654321, phase[3:0]};
      source65 = {phase[0], 60'hfedcba987654321, phase[3:0]};
      #0;
      `checkh(decoded7, phase[1] ? 7'h55 : 7'h00)
      `checkh(rotated33, {28'h7654321, phase[3:0], phase[0]})
      `checkh(rotated65, {60'hfedcba987654321, phase[3:0], phase[0]})
      #0 scheduled33 <= source33;
      #1;
      `checkh(scheduled33, {phase[0], 28'h7654321, phase[3:0]})
    end

    // Timed and zero-delayed resumptions in the same physical time slot.
    fork
      begin
        #2 source33 = 33'h1abcdef01;
      end
      begin
        #2;
        #0 source7 = 2;
        source65 = 65'h1fedcba9876543210;
        scheduled33 <= 33'h1abcdef01;
      end
    join
    #0;
    `checkh(decoded7, 7'h55)
    `checkh(rotated33, 33'h1579bde03)
    `checkh(rotated65, 65'h1fdb97530eca86421)
    #1;
    `checkh(scheduled33, 33'h1abcdef01)

    #0 source33 = MIXED33;
    source65 = MIXED65;
    #0;
    `checkh(rotated33, {MIXED33[31:0], MIXED33[32]})
    `checkh(rotated65, {MIXED65[63:0], MIXED65[64]})
    #0 scheduled33 <= MIXED33;
    #1;
    `checkh(scheduled33, MIXED33)

    // Recomputing an unchanged continuous RHS must not manufacture an event.
    // Take this baseline after startup and all preceding value transitions.
    before_events = decoded_events;
    #0;
    #0;
    #1;
    `checkd(decoded_events, before_events)
    `checkd(checks, 39)
    $display("Zero-domain checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
