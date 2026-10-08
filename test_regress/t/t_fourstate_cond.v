// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-License-Identifier: CC0-1.0

`ifdef VERILATOR
`define IMPURE_ONE ($c(1))
`else
`define IMPURE_ONE (|($random | $random))
`endif

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  static int calls = 0;
  bit [31:0] checks = 0;
  logic selector;
  logic branch_z;
  logic want_one_z, want_z_zero, want_z_one, want_zero_z;

  function logic f(logic a);
    if (a === 1'b1) $write("1");
    else if (a === 1'b0) $write("0");
    else if (a === 1'bx) $write("x");
    else if (a === 1'bz) $write("z");
    else $stop;
    $write("\n");
    return a;
  endfunction


  function logic bar();
    calls++;
    return 'x;
  endfunction

  initial begin
    if ((f(0) ? f(1) : f(0)) !== 0) $stop;
    if ((f(1) ? f(1) : f(0)) !== 1) $stop;
    if ((f('x) ? f(1) : f(0)) !== 'x) $stop;
    if ((f('x) ? f(1) : f(1)) !== 1) $stop;
    if ((f('z) ? f(1) : f(0)) !== 'x) $stop;
    if ((f('z) ? f(0) : f(0)) !== 0) $stop;
    if ((`IMPURE_ONE ? 0 : bar()) !== 0) $stop;
    if (calls !== 0) $stop;

    // These scalar forms must preserve a selected Z. Logical AND/OR rewrites
    // convert it to X, and an unknown selector merges unequal branches to X.
    branch_z = 1'bz;
    for (int state = 0; state < 4; state++) begin
      case (state)
        0: begin
          selector = 1'b0;
          want_one_z = 1'bz;
          want_z_zero = 1'b0;
          want_z_one = 1'b1;
          want_zero_z = 1'bz;
        end
        1: begin
          selector = 1'b1;
          want_one_z = 1'b1;
          want_z_zero = 1'bz;
          want_z_one = 1'bz;
          want_zero_z = 1'b0;
        end
        2, 3: begin
          selector = state == 2 ? 1'bx : 1'bz;
          want_one_z = 1'bx;
          want_z_zero = 1'bx;
          want_z_one = 1'bx;
          want_zero_z = 1'bx;
        end
      endcase
      #1;
      `checkh(selector ? 1'b1 : branch_z, want_one_z);
      `checkh(selector ? branch_z : 1'b0, want_z_zero);
      `checkh(selector ? branch_z : 1'b1, want_z_one);
      `checkh(selector ? 1'b0 : branch_z, want_zero_z);
    end
    if (checks !== 16) $fatal(1, "Conditional regression did not check every form");
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
