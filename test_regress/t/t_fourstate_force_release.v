// DESCRIPTION: Verilator: Release paired four-state forces on packed selections
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
  wire [3:0] done;
  wire [31:0] total_checks = w7.checks + w33.checks + w65.checks + w95.checks;
  force_release #(7) w7 (done[0]);
  force_release #(33) w33 (done[1]);
  force_release #(65) w65 (done[2]);
  force_release #(95) w95 (done[3]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done === 4'b1111);
    #1ps;
    $display("Four-state force release checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module force_release #(
    parameter int WIDTH = 7
) (
    output bit done = 0
);
  typedef struct packed {
    logic [WIDTH-1:0] upper;
    logic [WIDTH-1:0] lower;
  } pair_t;
  pair_t selected;
  logic [1:0][WIDTH-1:0] packed_words;
  logic [WIDTH-1:0] whole;
  int unsigned checks = 0;

  function automatic logic [WIDTH-1:0] force_pattern();
    for (int index = 0; index < WIDTH; ++index) begin
      case (index % 4)
        0: force_pattern[index] = 1'b0;
        1: force_pattern[index] = 1'b1;
        2: force_pattern[index] = 1'bx;
        3: force_pattern[index] = 1'bz;
      endcase
    end
  endfunction
  localparam logic [WIDTH-1:0] FORCED = force_pattern();

  initial begin
    selected = '0;
    packed_words = '0;
    whole = '0;
    #1;
    force selected.upper = FORCED;
    force packed_words[0] = FORCED;
    force whole = FORCED;
    #1;
    `checkh(selected.upper, FORCED);
    `checkh(selected.lower, '0);
    `checkh(packed_words[0], FORCED);
    `checkh(packed_words[1], '0);
    `checkh(whole, FORCED);
    // The underlying writes must not leak through either forced half.
    selected = '1;
    packed_words = '1;
    whole = '1;
    #1;
    `checkh(selected.upper, FORCED);
    `checkh(selected.lower, '1);
    `checkh(packed_words[0], FORCED);
    `checkh(packed_words[1], '1);
    `checkh(whole, FORCED);
    release selected.upper;
    release packed_words[0];
    release whole;
    #1;
    // IEEE 1800-2023 10.6.2: variables retain the forced value until next assigned.
    `checkh(selected.upper, FORCED);
    `checkh(packed_words[0], FORCED);
    `checkh(whole, FORCED);
    selected.upper = WIDTH'(checks);
    packed_words[0] = WIDTH'(checks);
    whole = WIDTH'(checks);
    #1;
    `checkh(selected.upper, WIDTH'(13));
    `checkh(packed_words[0], WIDTH'(13));
    `checkh(whole, WIDTH'(13));
    done = 1;
  end
endmodule
