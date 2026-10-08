// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  integer idly = 1;
  logic in = 1'b0;
  wire #idly d_int = in;
endmodule
