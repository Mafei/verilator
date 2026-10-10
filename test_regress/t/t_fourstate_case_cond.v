// DESCRIPTION: Verilator: Preserve X/Z while lowering conditional case items
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define STRINGIFY(x) `"x`"
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  int checks = 0;
  logic guard_value;
  logic [1:0] selector;
  logic [6:0] word = 7'b1010010;
  logic [2:0] index;
  logic [1:0] selectors[4] = '{2'b10, 2'b11, 2'b1x, 2'b1z};
  bit [3:0] expected_hits[4] = '{4'b0010, 4'b0001, 4'b0100, 4'b0100};
  bit branch_hit;
  bit unknown_hit;
  bit zero_hit;
  bit one_hit;

  always_comb begin
    case (selector)
      (guard_value ? 2'b10 : 2'b11): branch_hit = 1;
      default: branch_hit = 0;
    endcase
    case (1'bx)
      word[index]: unknown_hit = 1;
      default: unknown_hit = 0;
    endcase
    case (1'b0)
      word[index]: zero_hit = 1;
      default: zero_hit = 0;
    endcase
    case (1'b1)
      word[index]: one_hit = 1;
      default: one_hit = 0;
    endcase
  end

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    index = 0;
    for (int mode = 0; mode < 4; mode++) begin
      case (mode)
        0: guard_value = 1'b0;
        1: guard_value = 1'b1;
        2: guard_value = 1'bx;
        3: guard_value = 1'bz;
      endcase
      for (int sample = 0; sample < 4; sample ++) begin
        selector = selectors[sample];
        #1;
        `checkh(branch_hit, expected_hits[mode][sample])
      end
    end
    for (int sample = 0; sample < 5; sample ++) begin
      case (sample)
        0: index = 3'd0;
        1: index = 3'd6;
        2: index = 3'd7;
        3: index = 3'bxxx;
        4: index = 3'bzzz;
      endcase
      #1;
      `checkh(unknown_hit, sample >= 2)
      `checkh(zero_hit, sample == 0)
      `checkh(one_hit, sample == 1)
    end
    $display("Case item checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
