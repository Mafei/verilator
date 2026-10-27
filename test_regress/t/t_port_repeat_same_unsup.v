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
module t(input wire [12:0] d);
  wire [12:0] q;
  // Both external slots target one receiver; writer auditing must stay active.
  repeat_output u(q, q, d);
endmodule
