// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv, expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define checkh(gotv, expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

module t;
  tri1 [6:0] up7;
  tri0 [6:0] down7;
  tri1 [32:0] up33;
  tri0 [32:0] down33;
  tri1 [64:0] up65;
  tri0 [64:0] down65;
  bit [6:0] value = 0;
  tri1 [6:0] driven_up = value;
  tri0 [6:0] driven_down = value;
  wire [64:0] child_up;
  wire [64:0] child_down;
  pull_defaults child(child_up, child_down);

  initial begin
    for (int index = 0; index < 16; index++) begin
      value = 7'(index * 7);
      #1;
      `checkh(up7, 7'h7f);
      `checkh(down7, 7'h0);
      `checkh(up33, 33'h1ffffffff);
      `checkh(down33, 33'h0);
      `checkh(up65, 65'h1ffffffffffffffff);
      `checkh(down65, 65'h0);
      `checkh(child_up, 65'h1ffffffffffffffff);
      `checkh(child_down, 65'h0);
      `checkh(driven_up, value);
      `checkh(driven_down, value);
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module pull_defaults(output wire [64:0] up, output wire [64:0] down);
  tri1 [64:0] pulled_up;
  tri0 [64:0] pulled_down;
  assign up = pulled_up;
  assign down = pulled_down;
endmodule
