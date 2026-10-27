// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module repeat_output(o, o, d);
  output wire [12:0] o;
  input wire [12:0] d;
  assign o = d;
endmodule
module t;
  wire [25:0] q;
  repeat_output u(q[25:13], q[12:0], 13'b0);
endmodule
