// DESCRIPTION: Verilator: Four-state isolated drive semantics
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
module t;
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  wire [11:0] done;
  deassign_width #(1) w1 (done[0]);
  deassign_width #(7) w7 (done[1]);
  deassign_width #(17) w17 (done[2]);
  deassign_width #(33) w33 (done[3]);
  deassign_width #(65) w65 (done[4]);
  deassign_width #(129) w129 (done[5]);
  deassign_async #(1) p1 (done[6]);
  deassign_async #(7) p7 (done[7]);
  deassign_async #(17) p17 (done[8]);
  deassign_async #(33) p33 (done[9]);
  deassign_async #(65) p65 (done[10]);
  deassign_async #(129) p129 (done[11]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #100;
    `checkh(done, 12'hfff)
    $display("Deassign checks: %0d",
             w1.checks + w7.checks + w17.checks + w33.checks + w65.checks + w129.checks);
    $display("Async deassign checks: %0d",
             p1.checks + p7.checks + p17.checks + p33.checks + p65.checks + p129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

// Asynchronous procedural assignment plus clocked NBA must retain the assigned value on
// deassign. A generated retention copy is not an ordinary user blocking assignment.
module deassign_async #(
    parameter int WIDTH = 1
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  bit armed = 0;
  bit [31:0] events = 0;
  time last_change = 0;
  reg clock = 0, enable = 0;
  reg [WIDTH-1:0] source = '0, nba_value = '0, q = '0, pending = '0;
  wire [WIDTH-1:0] observed = q, observed_pending = pending;
  initial #1 armed = 1;
  always @(observed_pending) begin
    if (armed) begin
      events++;
      last_change = $time;
    end
  end
  always @(enable) begin
    if (enable == 1'b1) begin
      assign q = source;
      assign pending = source;
    end
    else if (enable == 1'b0) begin
      deassign q;
      deassign pending;
    end
  end
  always @(posedge clock) begin
    q <= nba_value;
    pending <= #2 nba_value;
  end
  initial begin
    #10;
    source = 'z;
    enable = 1;
    #1;
    `checkh(observed, 'z)
    `checkh(observed_pending, 'z)
    clock = 1;
    #1;
    `checkh(observed_pending, 'z)
    clock = 0;
    source = 'x;
    #2;
    `checkh(observed, 'x)
    `checkh(observed_pending, 'x)
    // The earlier hidden NBA has committed. Deassign must not expose its old raw value.
    enable = 0;
    #1;
    `checkh(observed, 'x)
    `checkh(observed_pending, 'x)
    source = '1;
    #1;
    `checkh(observed_pending, 'x)
    nba_value = '1;
    clock = 1;
    #1;
    `checkh(observed, '1)
    `checkh(observed_pending, 'x)
    clock = 0;
    #2;
    `checkh(observed_pending, '1)
    source = 'z;
    enable = 1;
    #1;
    `checkh(observed_pending, 'z)
    nba_value = '0;
    clock = 1;
    #1;
    `checkh(observed_pending, 'z)
    // Release before the delayed NBA commits: its captured value must now become visible.
    enable = 0;
    #1;
    source = 'x;
    #1;
    `checkh(observed, 'z)
    `checkh(observed_pending, '0)
    clock = 0;
    enable = 1;
    #1;
    `checkh(observed_pending, 'x)
    enable = 0;
    #1;
    `checkh(observed_pending, 'x)
    nba_value = 'z;
    clock = 1;
    #1;
    `checkh(observed, 'z)
    `checkh(observed_pending, 'x)
    source = '0;
    #2;
    `checkh(observed_pending, 'z)
    clock = 0;
    enable = 1;
    #1;
    `checkh(observed_pending, '0)
    enable = 'x;
    source = '1;
    #1;
    `checkh(observed_pending, '1)
    enable = 'z;
    source = 'z;
    #1;
    `checkh(observed_pending, 'z)
    enable = 0;
    #1;
    `checkh(observed_pending, 'z)
    source = '0;
    #1;
    `checkh(observed_pending, 'z)
    nba_value = 'x;
    clock = 1;
    #1;
    `checkh(observed, 'x)
    `checkh(observed_pending, 'z)
    clock = 0;
    #2;
    `checkh(observed_pending, 'x)
    enable = 'x;
    source = '1;
    #1;
    `checkh(observed_pending, 'x)
    enable = 'z;
    source = 'z;
    #1;
    `checkh(observed_pending, 'x)
    `checkd(events, 11)
    `checkd(last_change, 35)
    done = 1;
  end
endmodule

module deassign_width #(
    parameter int WIDTH = 1
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  bit armed = 0;
  bit [31:0] events = 0;
  time last_change = 0;
  reg clock = 0;
  reg [WIDTH-1:0] source = '0, nba_value = '0, q = '0;
  wire [WIDTH-1:0] observed = q;
  initial #1 armed = 1;
  always @(observed) begin
    if (armed) begin
      events++;
      last_change = $time;
    end
  end
  always @(posedge clock) q <= nba_value;
  initial begin
    #10;
    source = 'z;
    assign q = source;
    #1;
    `checkh(observed, 'z)
    q = '1;
    #1;
    `checkh(observed, 'z)
    clock = 1;
    #1;
    `checkh(observed, 'z)
    clock = 0;
    source = 'x;
    #1;
    `checkh(observed, 'x)
    nba_value = '1;
    clock = 1;
    #1;
    `checkh(observed, 'x)
    source = 'z;
    #1;
    `checkh(observed, 'z)
    deassign q;
    source = '0;
    #1;
    `checkh(observed, 'z)
    `checkd(events, 3)
    `checkd(last_change, 15)
    clock = 0;
    #1;
    clock = 1;
    #1;
    `checkh(observed, '1)
    q = 'x;
    #1;
    `checkh(observed, 'x)
    assign q = '0;
    #1;
    `checkh(observed, '0)
    clock = 0;
    #1;
    clock = 1;
    #1;
    `checkh(observed, '0)
    deassign q;
    #1;
    `checkh(observed, '0)
    q = 'z;
    #1;
    `checkh(observed, 'z)
    `checkd(events, 7)
    `checkd(last_change, 24)
    done = 1;
  end
endmodule
