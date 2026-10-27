// DESCRIPTION: Verilator: Missing ancestor task remains an ordinary user diagnostic
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module leaf;
  initial absent_task();
endmodule
module t;
  leaf child0();
endmodule
