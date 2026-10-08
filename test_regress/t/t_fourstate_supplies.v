// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  supply0 [6:0] ground;
  supply1 [6:0] power;

  initial begin
    #1;
    `checkh(ground, 7'b0000000);
    `checkh(power, 7'b1111111);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
