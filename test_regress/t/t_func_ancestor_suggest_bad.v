// DESCRIPTION: Verilator: Parameterized top typos retain ordinary suggestions
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t #(parameter N = 1);
  reg foobar;
  task boobar;
  endtask
  initial begin
    if (foobat) $stop;
    boobat;
  end
endmodule
