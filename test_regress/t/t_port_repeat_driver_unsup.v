// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps
module repeat_output(o, o, d, en);
  output wire o;
  input wire d, en;
`ifdef PROBE_DELAY
  assign #1 o = d;
`elsif PROBE_STRENGTH
  assign (strong0, strong1) o = d;
`elsif PROBE_TRISTATE
  bufif1 gate0(o, d, en);
`elsif PROBE_FORCE
  assign o = d;
  initial begin
    force o = 1'b0;
    #1;
    release o;
  end
`endif
endmodule
module t(input wire d, en);
  wire left, right;
  // Runtime inputs prevent a constant-enable primitive from disappearing.
  repeat_output u(left, right, d, en);
endmodule
