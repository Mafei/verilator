// SPDX-License-Identifier: CC0-1.0
// UNEXECUTED prototype boundary: ancestor functions require type/constant context support.
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
