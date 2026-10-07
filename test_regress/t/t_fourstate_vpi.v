// DESCRIPTION: Verilator: Four-state VPI vectors and X/Z value callbacks
// This file ONLY is placed under the Creative Commons Public Domain
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  logic [6:0] scalar /*verilator public_flat_rw*/;
  logic [64:0] wide /*verilator public_flat_rw*/;
  logic [47:0] memory [3:1] /*verilator public_flat_rw*/;
  initial begin
    scalar = '0;
    wide = '0;
    memory[2] = '0;
  end
endmodule
