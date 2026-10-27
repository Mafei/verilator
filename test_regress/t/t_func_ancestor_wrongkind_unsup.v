// DESCRIPTION: Verilator: Mixed-name ancestor lookup implementation boundary
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

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
