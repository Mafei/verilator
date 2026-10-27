// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t(o, o, d);
  output wire [12:0] o;
  input wire [12:0] d;
  assign o = d;
endmodule
