// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  import "DPI-C" function void inspect(input logic [6:0] values[]);
  logic [6:0] dynamic_values[];
  logic [6:0] queued_values[$];
  initial begin
    dynamic_values = new[1];
    dynamic_values[0] = 7'b10xz101;
    queued_values.push_back(7'b10xz101);
    inspect(dynamic_values);
    inspect(queued_values);
    $finish;
  end
endmodule
