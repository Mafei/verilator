// DESCRIPTION: Verilator: Named non-ANSI INPUT header alias boundary
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module named_input(.data(d), q);
  input wire [12:0] d;
  output wire [12:0] q;
  assign q = d;
endmodule
module t;
  wire [12:0] q;
  named_input u(13'b1010101010101, q);
endmodule
