// DESCRIPTION: Verilator: Ancestor functions require type and constant context support
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module leaf(output reg [7:0] value);
  initial value = lookup(8'd0);
endmodule
module t;
  wire [7:0] value;
  function [7:0] lookup(input [7:0] token);
    lookup = token + 8'd1;
  endfunction
  leaf child0(value);
endmodule
