// DESCRIPTION: Verilator: Observed assertion integration control
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ns / 1ps
module t;
  logic [64:0] sample;
  int phase;
  int reports = 0;
  task automatic report(input int saved_phase, input logic [64:0] saved_value);
    reports++;
    $display("OBS_SNAPSHOT phase=%0d value=%b", saved_phase, saved_value);
  endtask
  initial begin
    for (phase = 0; phase < 4; phase++) begin
      sample = phase[0] ? 65'b0zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10 : 65'b101xz01xz01xz01xz01xz01xz01xz01xz01xz01xz01xz01xz01xz01xz01xz01xz;
      assert #0 ((sample[64] === ~phase[0]) && $isunknown(sample)) report(phase, sample);
      else $fatal(1, "Observed X/Z condition mismatch");
      #1;
      if (reports != phase + 1) $fatal(1, "Missing observed report");
    end
    $display("OBS_SNAPSHOT_PASS reports=%0d", reports);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
