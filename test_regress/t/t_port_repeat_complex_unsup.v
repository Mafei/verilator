// DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module repeat_output(.left(o), .right(o), .drive(d));
  output wire [12:0] o;
  input wire [12:0] d;
  assign o = d;
endmodule
module t;
  wire [12:0] left, right;
  repeat_output u(.left(left), .right(right), .drive(13'b0));
endmodule
