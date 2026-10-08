// DESCRIPTION: Verilator: Four-state isolated drive semantics
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
module t;
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  wire [5:0] done;
  deassign_width #(1) w1 (done[0]);
  deassign_width #(7) w7 (done[1]);
  deassign_width #(17) w17 (done[2]);
  deassign_width #(33) w33 (done[3]);
  deassign_width #(65) w65 (done[4]);
  deassign_width #(129) w129 (done[5]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #100;
    `checkh(done, 6'b111111)
    $display("Deassign checks: %0d",
             w1.checks + w7.checks + w17.checks + w33.checks + w65.checks + w129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module deassign_width #(
    parameter int WIDTH = 1
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  reg clock = 0;
  reg [WIDTH-1:0] source = '0, nba_value = '0, q = '0;
  wire [WIDTH-1:0] observed = q;
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
    done = 1;
  end
endmodule
