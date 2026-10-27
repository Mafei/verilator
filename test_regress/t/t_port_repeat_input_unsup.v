// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module repeat_input(i, i, q);
  input wire i;
  output wire q;
  assign q = i;
endmodule
module t;
  wire q;
  repeat_input u(1'b0, 1'b1, q);
endmodule
