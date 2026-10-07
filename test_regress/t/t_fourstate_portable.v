// DESCRIPTION: Verilator: Relocated four-state installation and timing test
// This file ONLY is placed under the Creative Commons Public Domain
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t #(
  parameter bit REJECT_X = 0
);
  logic [6:0] value;
  logic [6:0] memory [3:1];
  logic [47:0] ram [0:31];
  typedef struct packed { logic [2:0] a; logic [3:0] b; } sample_t;
  sample_t sample;
  bit choose = 0;
  initial begin
    #1;
    if (value !== 7'bxxxxxxx) $fatal(1, "uninitialized value");
    value = 7'b10xz010;
    #1;
    if (value !== 7'b10xz010) $fatal(1, "X/Z preservation");
    for (int i = 0; i < 32; ++i) begin
      ram[i] = {41'b0, value};
      #1;
      if (ram[i] !== {41'b0, value}) $fatal(1, "48-bit RAM X/Z preservation");
    end
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
    if (REJECT_X && value !== 7'b0011101)
      $fatal(1, "FOURSTATE_UNKNOWN_REJECTED");
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
