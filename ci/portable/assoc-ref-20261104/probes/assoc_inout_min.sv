// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Public minimal probe; original t_assoc and all gold remain unchanged.
module assoc_inout_min(input logic clk);
  int cycle = 0;
  int result;
  int data[bit [31:0]];
  bit [31:0] selected_index[2];
  always @(posedge clk) begin
    cycle <= cycle + 1;
    data[5] = 1;
    data[9] = 2;
    result = data.last(selected_index[cycle + 1]);
  end
endmodule
