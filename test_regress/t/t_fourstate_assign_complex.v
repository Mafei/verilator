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
  logic [15:0] foo;
  bit [31:0] calls = 0;
  function Base fooo();
    calls = calls + 1;
    return this;
  endfunction
endclass

class Derived extends Base;
  logic [15:0] bar;
endclass

module t;
  initial begin
    static Derived foo = new;
    foo.foo = 2;
    `checkh(foo.fooo().foo, 16'b0000000000000010);
    `checkh(foo.calls, 32'd1);
    foo.foo[$c("0")] = 1;
    `checkh(foo.foo, 16'b0000000000000011);
    foo.foo[$c("3")+:2] = 2'd3;
    `checkh(foo.foo, 16'b0000000000011011);
    foo.fooo().foo[$c("3")+:2] = 2'bxz;
    `checkh(foo.foo, 16'b00000000000xz011);
    `checkh(foo.calls, 32'd2);
    foo.foo[$c("10")-:2] = 2'bxz;
    `checkh(foo.foo, 16'b00000xz0000xz011);
    foo.foo[$c("100")-:2] = 2'bxz;
    `checkh(foo.foo, 16'b00000xz0000xz011);
    {foo.foo, foo.bar} = 32'h71209zx6;
    `checkh(foo.foo, 16'h7120);
    `checkh(foo.bar, 16'h9zx6);
    for (int i = 0; i < 4; i++) begin
      foo.fooo().foo[i +: 2] = 2'bxz;
      `checkh(foo.calls, 32'(i + 3));
      `checkh(foo.foo[i +: 2], 2'bxz);
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
