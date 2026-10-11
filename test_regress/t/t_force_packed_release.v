// DESCRIPTION: Verilator: Constant packed selector release paths
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [1:0] done;
  wire [31:0] total_checks = w65.checks + w95.checks;
  packed_release #(65) w65 (done[0]);
  packed_release #(95) w95 (done[1]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done === 2'b11);
    #1ps;
    $display("Packed selector release checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module packed_release #(
    parameter int WIDTH = 65
) (
    output bit done = 0
);
  bit [1:0][WIDTH-1:0] words;
  int unsigned checks = 0;

  function automatic bit [WIDTH-1:0] force_pattern();
    for (int index = 0; index < WIDTH; ++index) force_pattern[index] = 1'(index % 2);
  endfunction
  localparam bit [WIDTH-1:0] LOW = force_pattern();
  localparam bit [WIDTH-1:0] HIGH = ~LOW;

  initial begin
    words = '0;
    #1;
    force words[0] = LOW;
    force words[1] = HIGH;
    #1;
    `checkh(words[0], LOW);
    `checkh(words[1], HIGH);
    words = '0;
    #1;
    `checkh(words[0], LOW);
    `checkh(words[1], HIGH);
    release words[0];
    #1;
    `checkh(words[0], LOW);
    `checkh(words[1], HIGH);
    words[0] = WIDTH'(checks);
    #1;
    `checkh(words[0], WIDTH'(6));
    `checkh(words[1], HIGH);
    release words[1];
    #1;
    `checkh(words[0], WIDTH'(6));
    `checkh(words[1], HIGH);
    words[1] = WIDTH'(checks);
    #1;
    `checkh(words[0], WIDTH'(6));
    `checkh(words[1], WIDTH'(10));
    force words[0] = HIGH;
    force words[1] = LOW;
    #1;
    `checkh(words[0], HIGH);
    `checkh(words[1], LOW);
    // Nested duplicate selections keep their individual release paths.
    release {{words[1], words[1]}, words[0]};
    #1;
    `checkh(words[0], HIGH);
    `checkh(words[1], LOW);
    words = '0;
    #1;
    `checkh(words[0], '0);
    `checkh(words[1], '0);
    done = 1;
  end
endmodule
