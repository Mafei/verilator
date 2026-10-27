// DESCRIPTION: Verilator: Parameterized ancestor task context boundary
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module leaf(output reg [7:0] value);
  initial emit(value);
endmodule
module host #(parameter W = 8)(output wire [7:0] value);
  task emit(output [W-1:0] result);
    result = {W{1'b1}};
  endtask
  leaf child0(value);
endmodule
module t;
  wire [7:0] value;
  host h(value);
endmodule
