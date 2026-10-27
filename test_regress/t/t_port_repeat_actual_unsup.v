// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Only the later-instance profile uses parameters, so it tests the same specialization.
`ifdef PROBE_LATER_SECOND
module repeat_output #(parameter integer W = 13) (o, o, d);
  output wire [W-1:0] o;
  input wire [W-1:0] d;
`else
module repeat_output(o, o, d);
  output wire [12:0] o;
  input wire [12:0] d;
`endif
  assign o = d;
endmodule
module t;
  wire [25:0] q;
`ifdef PROBE_SECOND_SELECTED
  wire [12:0] good;
  repeat_output u(good, q[12:0], 13'b0);
`elsif PROBE_LATER_SECOND
  wire [12:0] first_left, first_right, later_left;
  repeat_output #(.W(13)) first(first_left, first_right, 13'b0);
  repeat_output #(.W(13)) later(later_left, q[12:0], 13'b0);
`elsif PROBE_NC_SECOND
  repeat_output u(, q[12:0], 13'b0);
`else
  // Original first-slot rejection remains the default profile.
  repeat_output u(q[25:13], q[12:0], 13'b0);
`endif
endmodule
