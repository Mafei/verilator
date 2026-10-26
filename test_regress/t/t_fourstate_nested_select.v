// DESCRIPTION: Verilator: Packed element offsets preserve bounds before nested reads
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: step=%0d got=%b expected=%b\n", `__FILE__, `__LINE__, step, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  localparam logic [6:0] P70_E = 7'b0xz1010;
  localparam logic [6:0] P70_O = 7'b1zx0101;
  localparam logic [6:0] P71_E = 7'bz10x011;
  localparam logic [6:0] P71_O = 7'b10z1100;
  localparam logic [32:0] P330_E = {1'b0, {8{4'b10zx}}};
  localparam logic [32:0] P330_O = {1'b1, {8{4'b01xz}}};
  localparam logic [32:0] P331_E = {1'bx, {8{4'b00z1}}};
  localparam logic [32:0] P331_O = {1'bz, {8{4'b1100}}};
  logic [1:0][6:0] bank7;
  logic [1:0][32:0] bank33;
  logic [31:0] row7;
  logic [31:0] row33;
  logic [94:0] row95;
  logic r7 = 0;
  logic r33 = 0;
  logic [6:0] w7 = '0;
  logic [32:0] w33 = '0;
  logic once;
  int step;
  int checks = 0;
  int calls = 0;

  function automatic logic [94:0] next_row;
    calls++;
    return row95;
  endfunction

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, r7, r33, w7, w33);
    for (step = 0; step < 8; step++) begin
      bank7 = step[0] ? {P71_O, P70_O} : {P71_E, P70_E};
      bank33 = step[0] ? {P331_O, P330_O} : {P331_E, P330_E};
      row7 = 0;
      row33 = 0;
      row95 = 0;
      case (step)
        1: begin row7 = 1; row33 = 1; row95 = 1; end
        2: begin row7 = 2; row33 = 2; row95 = 2; end
        3: begin
          // These products are 2**32-4; a narrow nested +4 would alias offset0.
          row7 = 32'd613566756;
          row33 = 32'd130150524;
          row95 = 95'd1 << 64;
        end
        4: begin
          row7 = 32'd613566757;
          row33 = 32'd130150525;
          row95 = (95'd1 << 64) + 95'd1;
        end
        5: begin row7 = '1; row33 = '1; row95 = '1; end
        6: begin row7[31] = 1'bx; row33[31] = 1'bz; row95[94] = 1'bx; end
        7: row95 = 1;
        default: begin end
      endcase
      #1;
      // The wide row types intentionally test complete packed element domains.
      // verilator lint_off WIDTHTRUNC
      // verilator lint_off WIDTHEXPAND
      r7 = bank7[row7][4];
      r33 = bank33[row33][4];
      w7 = bank7[row95];
      w33 = bank33[row95];
      // verilator lint_on WIDTHEXPAND
      // verilator lint_on WIDTHTRUNC
      #1;
      case (step)
        0: begin
          `checkh(r7, P70_E[4]); `checkh(r33, P330_E[4]);
          `checkh(w7, P70_E); `checkh(w33, P330_E);
        end
        1: begin
          `checkh(r7, P71_O[4]); `checkh(r33, P331_O[4]);
          `checkh(w7, P71_O); `checkh(w33, P331_O);
        end
        7: begin
          `checkh(r7, P70_O[4]); `checkh(r33, P330_O[4]);
          `checkh(w7, P71_O); `checkh(w33, P331_O);
        end
        default: begin
          `checkh(r7, 1'bx); `checkh(r33, 1'bx);
          `checkh(w7, 7'bx); `checkh(w33, 33'bx);
        end
      endcase
      $display("NESTED SELECT step=%0d t=%0t r7=%b r33=%b w7=%b w33=%b",
               step, $time, r7, r33, w7, w33);
    end
    // verilator lint_off WIDTHTRUNC
    // verilator lint_off WIDTHEXPAND
    once = bank7[next_row()][0];
    // verilator lint_on WIDTHEXPAND
    // verilator lint_on WIDTHTRUNC
    `checkh(once, 1'b0);
    `checkh(calls, 1);
    #1;
    $display("Nested selection checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
