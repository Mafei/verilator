// SPDX-License-Identifier: CC0-1.0
// Mixed-name ancestor lookup is outside this prototype's supported subset.
module leaf;
  initial emit();
endmodule
module middle;
  reg emit;
  leaf child0();
endmodule
module t;
  task emit;
  endtask
  middle child0();
endmodule
