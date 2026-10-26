// DESCRIPTION: Verilator: Known gap in a four-state wait predicate
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  logic [4:0] state = '0;
  bit woke = 0;
  initial begin
    wait (&state);
    woke = 1;
  end
  initial begin
    #1;
    state = '1;
    #1;
    if (!woke) $fatal(1, "wait did not reevaluate the four-state reduction");
    $display("WAIT_REDUCTION_PASS");
    $finish;
  end
endmodule
