// DESCRIPTION: Verilator: Positional dynamic-array constructor X/Z and call counts
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
// verilog_format: on

module t;
  logic [3:0] source[];
  logic [3:0] copied[];
  bit [31:0] calls = 0;
  bit [31:0] checks = 0;

  function automatic logic [3:0] next_word(input logic [3:0] value);
    calls++;
    return value;
  endfunction

  initial begin
    source = new[3] ('{next_word(4'bx1z0), next_word(4'b0zx1), 4'bzzxx});
    `checkh(calls, 32'd2);
    `checkh(source.size(), 32'd3);
    `checkh(source[0], 4'bx1z0);
    `checkh(source[1], 4'b0zx1);
    `checkh(source[2], 4'bzzxx);
    copied = new[3] (source);
    `checkh(calls, 32'd2);
    `checkh(copied.size(), 32'd3);
    `checkh(copied[0], 4'bx1z0);
    `checkh(copied[1], 4'b0zx1);
    `checkh(copied[2], 4'bzzxx);
    source[0] = 4'b1010;
    `checkh(copied[0], 4'bx1z0);
    source = new[1] ('{next_word(4'bz0x1)});
    `checkh(calls, 32'd3);
    `checkh(source.size(), 32'd1);
    `checkh(source[0], 4'bz0x1);
    `checkh(copied[2], 4'bzzxx);
    $display("CONS_COPY_PASS checks=%0d calls=%0d source=%b copied=%b,%b,%b",
             checks, calls, source[0], copied[0], copied[1], copied[2]);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
