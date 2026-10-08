// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// Only actual or potential overlapping contributions are resolver candidates.
// Static disjoint partial writes and unpacked element writes retain legacy paths.
module t;
  logic [6:0] source_a = 7'h15, source_b = 7'h2a;
`ifdef RESOLVE_CASE_1
  wire [6:0] resolved;
  assign resolved = source_a;
  assign resolved = source_b;
  assign resolved = ~source_a;
  assign resolved = ~source_b;
`elsif RESOLVE_CASE_2
  wire [6:0] resolved;
  assign resolved = source_a;
  assign resolved[3:0] = source_b[3:0];
`elsif RESOLVE_CASE_3
  wire [6:0] resolved;
  assign resolved[6:3] = source_a[3:0];
  assign resolved[4:0] = source_b[4:0];
`elsif RESOLVE_CASE_4
  wire [6:0] resolved;
  // Identical partial ranges can be split into a variable before Fourstate.
  // Read only the selected range to preserve that optimization opportunity.
  wire [3:0] observed = resolved[3:0];
  assign resolved[3:0] = source_a[3:0];
  assign resolved[3:0] = source_b[3:0];
`elsif RESOLVE_CASE_5
  wire [6:0] resolved;
  assign (strong1, strong0) resolved = source_a;
  assign resolved = source_b;
`elsif RESOLVE_CASE_6
  wire [6:0] resolved;
  assign #1 resolved = source_a;
  assign resolved = source_b;
`elsif RESOLVE_CASE_7
  wire [6:0] #1 resolved;
  assign resolved = source_a;
  assign resolved = source_b;
`elsif RESOLVE_CASE_8
  resolver_local child();
  assign child.resolved = source_a;
  assign child.resolved = source_b;
`elsif RESOLVE_CASE_9
  wire [6:0] resolved;
  assign resolved = source_a;
  resolver_output child(source_b, resolved);
`elsif RESOLVE_CASE_10
  wire [6:0] resolved, other;
  alias resolved = other;
  assign resolved = source_a;
  assign resolved = source_b;
`elsif RESOLVE_CASE_11
  wire [6:0] resolved;
  assign resolved = source_a;
  assign resolved = source_b;
  initial begin
    #1;
    force resolved = 7'h3f;
    #1;
    release resolved;
  end
`elsif RESOLVE_CASE_12
  wire [6:0] resolved /* verilator public_flat_rw */;
  assign resolved = source_a;
  assign resolved = source_b;
`elsif RESOLVE_CASE_13
  wire [6:0] resolved;
  bit [31:0] calls = 0;
  function automatic logic [6:0] counted(input logic [6:0] value);
    calls++;
    return value;
  endfunction
  assign resolved = counted(source_a);
  assign resolved = source_b;
`elsif RESOLVE_CASE_14
  wire [6:0] result;
  resolver_port child(source_a, source_b, result);
`else
  initial $fatal(1, "Select one RESOLVE_CASE for the unsupported test");
`endif

  initial begin
    #2;
    source_a = 'z;
    #2;
    source_b = 'x;
    #2;
`ifdef RESOLVE_CASE_4
    $display("Selected overlapping value: %b", observed);
`endif
    $finish;
  end
endmodule

module resolver_local;
  wire [6:0] resolved;
endmodule

module resolver_output(input wire [6:0] source, output wire [6:0] result);
  assign result = source;
endmodule

module resolver_port(input wire [6:0] source_a, input wire [6:0] source_b,
                     output wire [6:0] resolved);
  assign resolved = source_a;
  assign resolved = source_b;
endmodule

`ifdef RESOLVE_CASE_15
// ANSI output without an explicit net keyword has implicit net semantics.
module t_ansi;
  logic [6:0] source_a = 7'h15, source_b = 7'h2a;
  wire [6:0] result;
  resolver_ansi child(source_a, source_b, result);
  initial begin
    #1;
    source_a = 'z;
    #1;
    $display("Implicit ANSI output: %b", result);
    $finish;
  end
endmodule

module resolver_ansi(input [6:0] source_a, source_b, output [6:0] resolved);
  assign resolved = source_a;
  assign resolved = source_b;
endmodule
`endif

`ifdef RESOLVE_CASE_16
// The same implicit output net in a non-ANSI declaration must fail closed.
module t_nonansi;
  logic [6:0] source_a = 7'h15, source_b = 7'h2a;
  wire [6:0] result;
  resolver_nonansi child(source_a, source_b, result);
  initial begin
    #1;
    source_a = 'z;
    #1;
    $display("Implicit non-ANSI output: %b", result);
    $finish;
  end
endmodule

module resolver_nonansi(source_a, source_b, resolved);
  input [6:0] source_a, source_b;
  output [6:0] resolved;
  assign resolved = source_a;
  assign resolved = source_b;
endmodule
`endif

`ifdef RESOLVE_CASE_17
// A declaration fallback does not excuse a real hierarchical continuous writer.
module t_default_writer;
  logic [6:0] source_a = '0, source_b = '1;
  wire [6:0] result;
  resolver_default_writer child(.i(source_b), .o(result));
  assign child.i = source_a;
  initial begin
    #1;
    source_a = 'z;
    #1;
    $display("Default input with real writer: %b", result);
    $finish;
  end
endmodule

module resolver_default_writer(input wire [6:0] i = 7'b10zx101,
                               output wire [6:0] o);
  assign o = i;
endmodule
`endif
