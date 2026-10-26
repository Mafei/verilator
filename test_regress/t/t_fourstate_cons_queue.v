// DESCRIPTION: Verilator: Two-state queue constructor and splice call counts
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
// verilog_format: on

module t;
  typedef bit [7:0] word_t;
  word_t words[$];
  word_t copied[$];
  bit [31:0] calls = 0;
  bit [31:0] checks = 0;

  function automatic bit [7:0] next_word(input bit [7:0] value);
    calls++;
    return value;
  endfunction

  initial begin
    words = '{next_word(8'h12), next_word(8'h34)};
    `checkh(calls, 32'd2);
    `checkh(words.size(), 32'd2);
    `checkh(words[0], 8'h12);
    `checkh(words[1], 8'h34);
    copied = {8'h56, words, 8'h78};
    `checkh(copied.size(), 32'd4);
    `checkh(copied[0], 8'h56);
    `checkh(copied[1], 8'h12);
    `checkh(copied[2], 8'h34);
    `checkh(copied[3], 8'h78);
    words[0] = 8'hff;
    `checkh(copied[1], 8'h12);
    `checkh(calls, 32'd2);
    words = '{word_t'(8'hxz)};
    `checkh(words.size(), 32'd1);
    `checkh(words[0], 8'h00);
    $display("CONS_QUEUE_PASS checks=%0d calls=%0d words=%h copied=%h,%h,%h,%h",
             checks, calls, words[0], copied[0], copied[1], copied[2], copied[3]);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
