// SPDX-License-Identifier: CC0-1.0
// UNEXECUTED: source imports in the affected cone must reject before clone/binding.
package p;
  task emit(output reg [7:0] value);
    value = 8'h22;
  endtask
endpackage
module leaf(output reg [7:0] value);
  initial begin #1; emit(value); end
endmodule
module middle(output wire [7:0] value);
  import p::*;
  leaf child0(value);
endmodule
module t;
  wire [7:0] value;
  task emit(output reg [7:0] value);
    value = 8'h11;
  endtask
  middle child0(value);
endmodule
