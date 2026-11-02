// DESCRIPTION: Verilator: Two-state queue constructors, splices and keyed defaults
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
// verilog_format: on

module t;
  typedef bit [7:0] word_t;
  word_t words[$];
  word_t copied[$];
  bit [31:0] calls = 0;
  bit [31:0] checks = 0;
  wire [3:0] keyed_done;
  queue_default_case #(7) keyed7 (keyed_done[0]);
  queue_default_case #(33) keyed33 (keyed_done[1]);
  queue_default_case #(65) keyed65 (keyed_done[2]);
  queue_default_case #(95) keyed95 (keyed_done[3]);
  wire [31:0] total_checks = checks + keyed7.checks + keyed33.checks + keyed65.checks + keyed95.checks;

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
    wait (&keyed_done);
    #1ps;
    if (total_checks != 77) $fatal(1, "Missing queue constructor checks");
    $display("CONS_QUEUE_PASS checks=%0d calls=%0d words=%h copied=%h,%h,%h,%h",
             total_checks, calls, words[0], copied[0], copied[1], copied[2], copied[3]);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module queue_default_case #(parameter int WIDTH = 7) (output bit done = 0);
  typedef bit [WIDTH-1:0] word_t;
  logic [WIDTH-1:0] default_value;
  word_t expected;
  word_t values[$];
  bit [31:0] checks = 0;

  initial begin
    for (int phase = 0; phase < 4; phase++) begin
      case (phase)
        0: begin
          default_value = '1;
          default_value[1:0] = 2'bxz;
          expected = '1;
          expected[1:0] = 2'b00;
        end
        1: begin
          default_value = '0;
          default_value[WIDTH-1] = 1'b1;
          default_value[WIDTH-2 -: 2] = 2'bzx;
          expected = '0;
          expected[WIDTH-1] = 1'b1;
        end
        2: begin default_value = 'x; expected = '0; end
        3: begin default_value = 'z; expected = '0; end
        default: $fatal(1, "Invalid phase");
      endcase
      #1;
      values = '{2:word_t'('1), default:default_value};
      #1;
      `checkh(values.size(), 32'd3);
      `checkh(values[0], expected);
      `checkh(values[1], expected);
      `checkh(values[2], word_t'('1));
    end
    done = 1;
  end
endmodule
