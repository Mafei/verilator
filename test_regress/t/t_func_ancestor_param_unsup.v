// SPDX-License-Identifier: CC0-1.0
// UNEXECUTED prototype boundary: parent parameter specialization is not guessed.
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
