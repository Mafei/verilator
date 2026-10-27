// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module repeat_inout(a, a);
  inout wire a;
endmodule
module t;
  wire left, right;
  repeat_inout u(left, right);
endmodule
