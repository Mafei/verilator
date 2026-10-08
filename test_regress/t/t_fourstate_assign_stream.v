// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  logic a, b;
  logic [1:0] c;
  assign {>>{a, b}} = c;

  initial begin
    c = 2'b1x;
    #1;
    `checkh(a, 1'b1);
    `checkh(b, 1'bx);
    c = 2'bz0;
    #1;
    `checkh(a, 1'bz);
    `checkh(b, 1'b0);
    for (int i = 0; i < 4; i++) begin
      c = 2'(i);
      #1;
      `checkh({a, b}, 2'(i));
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
