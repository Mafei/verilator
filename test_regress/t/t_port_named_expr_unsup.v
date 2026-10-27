// DESCRIPTION: Verilator: Named OUTPUT header part-select boundary
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// The bare q also declares the full internal I/O in the header. The named
// part-select is legal, but is outside the direct-wire alias subset.
module t(.part(q[6:0]), q);
  output wire [12:0] q;
  assign q = 13'b1010101010101;
endmodule
