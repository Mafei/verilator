// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

class Base;
  logic [14:0] value;
  bit [31:0] calls = 0;

  function Base selected();
    calls = calls + 1;
    return this;
  endfunction
endclass

class Derived extends Base;
endclass

module t;
  logic [14:0] expected;
  logic [14:0] observed;
  bit [31:0] calls_before;

  initial begin
    static Derived item = new;
    for (int i = 0; i < 8; i++) begin
      case (i % 4)
        0: expected = 15'((i * 13) ^ 'h2355);
        1: expected = 15'b101x001z1010010;
        2: expected = 'x;
        3: expected = 'z;
      endcase
      calls_before = item.calls;
      item.selected().value = expected;
      `checkh(item.calls, calls_before + 1);
      `checkh(item.value, expected);
      observed = item.selected().value;
      `checkh(item.calls, calls_before + 2);
      `checkh(observed, expected);
      #1;
    end
    `checkh(item.calls, 32'd16);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
