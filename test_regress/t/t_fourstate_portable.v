// DESCRIPTION: Verilator: Relocated four-state installation and timing test
// This file ONLY is placed under the Creative Commons Public Domain
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  logic [6:0] value;
  logic [6:0] memory [3:1];
  typedef struct packed { logic [2:0] a; logic [3:0] b; } sample_t;
  sample_t sample;
  bit choose = 0;
  initial begin
    #1;
    if (value !== 7'bxxxxxxx) $fatal(1, "uninitialized value");
    value = 7'b10xz010;
    #1;
    if (value !== 7'b10xz010) $fatal(1, "X/Z preservation");
    memory[2] = value;
    sample = value;
    #1;
    if (memory[2] !== value || sample !== value) $fatal(1, "aggregate split");
    if (!$isunknown(value)) $fatal(1, "isunknown");
    choose = 1;
    value = choose ? 7'b0011101 : 7'b1110000;
    #1;
    if (value !== 7'b0011101 || $countones(value) != 4) $fatal(1, "known value");
    value = 7'bxxxxxxx;
    #1;
    if ($test$plusargs("reject_x") && value !== 7'b0011101)
      $fatal(1, "FOURSTATE_UNKNOWN_REJECTED");
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
