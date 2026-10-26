// DESCRIPTION: Verilator: Keyed dynamic-array X/Z defaults and size evaluation
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
// verilog_format: on

module t;
  logic [3:0] words[];
  logic [3:0] copied[];
  bit [31:0] value_calls = 0;
  bit [31:0] size_calls = 0;
  bit [31:0] checks = 0;

  function automatic logic [3:0] next_word(input logic [3:0] value);
    value_calls++;
    return value;
  endfunction

  function automatic bit [31:0] next_size(input bit [31:0] value);
    size_calls++;
    return value;
  endfunction

  initial begin
    words = new[next_size(4)] ('{1: next_word(4'bx1z0),
                                3: next_word(4'b0zx1), default: next_word(4'bz0x1)});
    `checkh(size_calls, 32'd1);
    `checkh(value_calls, 32'd3);
    `checkh(words.size(), 32'd4);
    `checkh(words[0], 4'bz0x1);
    `checkh(words[1], 4'bx1z0);
    `checkh(words[2], 4'bz0x1);
    `checkh(words[3], 4'b0zx1);
    copied = new[4] (words);
    words[1] = 4'b1010;
    `checkh(copied[0], 4'bz0x1);
    `checkh(copied[1], 4'bx1z0);
    `checkh(copied[2], 4'bz0x1);
    `checkh(copied[3], 4'b0zx1);
    words = new[next_size(2)] ('{default: next_word(4'bzzxx)});
    `checkh(size_calls, 32'd2);
    `checkh(value_calls, 32'd4);
    `checkh(words.size(), 32'd2);
    `checkh(words[0], 4'bzzxx);
    `checkh(words[1], 4'bzzxx);
    $display("CONS_KEYED_PASS checks=%0d size_calls=%0d value_calls=%0d words=%b,%b",
             checks, size_calls, value_calls, words[0], words[1]);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
