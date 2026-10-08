// DESCRIPTION: Verilator: Monitor final values once in the Postponed region
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
module t;
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  logic [6:0] source;
  logic [6:0] scheduled = 0;
  logic [128:0] wide;
  wire [6:0] decoded = scheduled[1] ? 7'h55 : 7'h00;
`ifdef MONITOR_XZ
  localparam logic [6:0] MIXED = 7'b10zx010;
  localparam logic [6:0] MASK_CHANGE = 7'b10xx010;
  localparam logic [128:0] WIDE_MIXED = {1'bz, 128'b0};
  localparam logic [128:0] WIDE_CHANGED = {1'bx, 128'b0};
`else
  localparam logic [6:0] MIXED = 7'b1010010;
  localparam logic [6:0] MASK_CHANGE = 7'b1000010;
  localparam logic [128:0] WIDE_MIXED = {1'b1, 128'b0};
  localparam logic [128:0] WIDE_CHANGED = {1'b0, 128'b0};
`endif

  initial begin
    source = 0;
    wide = 0;
    $monitor("M0 %0t %b %b %b %b", $time, source, scheduled, decoded, wide);
    #0 source = 2;
    #0 source = 1;
    source = 2;
    scheduled <= 2;
    wide = 129'h100000000000000000000000000000001;
    #1;
    `checkh(source, 7'h02)
    `checkh(scheduled, 7'h02)
    `checkh(decoded, 7'h55)
    `checkh(wide, 129'h100000000000000000000000000000001)
    source = 3;
    source = 2;
    #0 source = 4;
    #0 source = 5;
    scheduled <= 5;
    wide = 129'h2;
    #1;
    `checkh(source, 7'h05)
    `checkh(scheduled, 7'h05)
    `checkh(decoded, 7'h00)
    `checkh(wide, 129'h2)
    $monitoroff;
    source = MIXED;
    wide = WIDE_MIXED;
    #1;
    `checkh(source, MIXED)
    `checkh(wide, WIDE_MIXED)
    $monitoron;
    #1 $monitoron;  // An already enabled monitor must still print unchanged values.
    #1 source = 1;
    #0 source = MIXED;  // A transient change still requests one final-value line.
    #1 $monitoroff;
    #0 $monitoron;
    #0 $monitoroff;  // Disabling future changes keeps the already queued on request.
    #1 $monitoron;
    #0 $monitor("M1 %0t %b %b %b %b", $time, source, scheduled, decoded, wide);
    #1;
    repeat (2) begin
      // Re-executing the same registration requests a line without a value change.
      $monitor("M1 %0t %b %b %b %b", $time, source, scheduled, decoded, wide);
      #1;
    end
    source = MASK_CHANGE;
    wide = WIDE_CHANGED;
    #1;
    `checkh(source, MASK_CHANGE)
    `checkh(wide, WIDE_CHANGED)
    $monitor("TIME %0t", $time);  // Time alone is not an argument-change trigger.
    source = 0;
    wide = 0;
    #1;
    `checkh(decoded, 7'h00)
    #0;
    #1 $monitoron;
    #1 $monitoroff;
    $display("Monitor checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish(0);
  end
endmodule
