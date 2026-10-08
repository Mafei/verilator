// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Each selected case is legal SystemVerilog outside the bounded local,
// whole packed, single default-strength continuous-driver implementation.
module t;
  logic [6:0] source = 7'h15;

`ifdef PULL_CASE_1
  tri0 [6:0] pulled;
  logic [6:0] other = 7'h2a;
  always @(source) other = ~source;
  assign pulled = source;
  assign pulled = other;
`elsif PULL_CASE_2
  tri1 [6:0] pulled;
  assign pulled[3:0] = source[3:0];
`elsif PULL_CASE_3
  tri0 [6:0] pulled;
  pull_output child(source, pulled);
`elsif PULL_CASE_4
  pull_local child();
  assign child.pulled = source;
`elsif PULL_CASE_5
  tri0 [6:0] pulled;
  wire [6:0] other;
  alias pulled = other;
  assign pulled = source;
`elsif PULL_CASE_6
  tri1 [6:0] pulled;
  assign pulled = source;
  initial begin
    #1;
    force pulled = 7'h2a;
    #1;
    release pulled;
  end
`elsif PULL_CASE_7
  tri0 [6:0] pulled;
  assign #1 pulled = source;
`elsif PULL_CASE_8
  tri1 [6:0] #1 pulled;
  assign pulled = source;
`elsif PULL_CASE_9
  tri0 [6:0] pulled;
  assign (weak1, weak0) pulled = source;
`elsif PULL_CASE_10
  tri1 [6:0] pulled /* verilator forceable */;
  assign pulled = source;
`elsif PULL_CASE_11
  wire [6:0] result;
  pull_port child(source, result);
`elsif PULL_CASE_12
  tri0 [6:0] pulled [0:1];
  assign pulled[0] = source;
`elsif PULL_CASE_13
  bit [31:0] calls = 0;
  function automatic logic [6:0] counted(input logic [6:0] value);
    calls++;
    return value;
  endfunction
  tri1 [6:0] pulled;
  assign pulled = counted(source);
`elsif PULL_CASE_14
  tri1 [6:0] pulled /* verilator public_flat_rw */;
  assign pulled = source;
`else
  initial $fatal(1, "Select one PULL_CASE for the unsupported test");
`endif

  initial begin
    #2;
    source = 'z;
    #2;
    source = 'x;
    #2;
    $finish;
  end
endmodule

module pull_output(input wire [6:0] source, output wire [6:0] result);
  assign result = source;
endmodule

module pull_local;
  tri0 [6:0] pulled;
endmodule

module pull_port(input wire [6:0] source, output tri1 [6:0] pulled);
  assign pulled = source;
endmodule
