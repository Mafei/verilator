// DESCRIPTION: Verilator: Primary API input initialization preserves internal X/Z
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t (
    input implicit_scalar,
    input var logic variable_scalar,
    input [6:0] implicit7,
    input logic [6:0] typed7,
    input wire logic [6:0] wire7,
    input var logic [6:0] variable7,
    // Ascending API ranges deliberately test bit ordering.
    // verilator lint_off ASCRANGE
    input logic [0:6] ascending7,
    // verilator lint_on ASCRANGE
    input [32:0] implicit33,
    input logic [32:0] typed33,
    input wire logic [32:0] wire33,
    input var logic [32:0] variable33,
    // Ascending API ranges deliberately test bit ordering.
    // verilator lint_off ASCRANGE
    input logic [0:32] ascending33,
    // verilator lint_on ASCRANGE
    input [64:0] implicit65,
    input logic [64:0] typed65,
    input wire logic [64:0] wire65,
    input var logic [64:0] variable65,
    // Ascending API ranges deliberately test bit ordering.
    // verilator lint_off ASCRANGE
    input logic [0:64] ascending65,
    // verilator lint_on ASCRANGE
    input [94:0] implicit95,
    input logic [94:0] typed95,
    input wire logic [94:0] wire95,
    input var logic [94:0] variable95,
    // Ascending API ranges deliberately test bit ordering.
    // verilator lint_off ASCRANGE
    input logic [0:94] ascending95,
    // verilator lint_on ASCRANGE
    input [128:0] implicit129,
    input logic [128:0] typed129,
    input wire logic [128:0] wire129,
    input var logic [128:0] variable129,
    // Ascending API ranges deliberately test bit ordering.
    // verilator lint_off ASCRANGE
    input logic [0:128] ascending129,
    // verilator lint_on ASCRANGE
    output logic [6:0] primary_variable7,
    output wire logic [32:0] primary_wire33,
    output var logic [64:0] primary_explicit65
);
  logic [6:0] internal_variable7;
  wire logic [32:0] internal_wire33;
  wire logic [64:0] child_variable65;
  wire logic [94:0] child_wire95;
  int unsigned checks = 0;
  api_internal_defaults internal_source (child_variable65, child_wire95);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    for (int sample = 0; sample < 3; ++sample) begin
      #1;
`ifdef EXPECT_PRIMARY_API
      `checkh(implicit_scalar, 1'b0);
      `checkh(variable_scalar, 1'b0);
      `checkh(implicit7, 7'b0);
      `checkh(typed7, 7'b0);
      `checkh(wire7, 7'b0);
      `checkh(variable7, 7'b0);
      `checkh(ascending7, 7'b0);
      `checkh(implicit33, 33'b0);
      `checkh(typed33, 33'b0);
      `checkh(wire33, 33'b0);
      `checkh(variable33, 33'b0);
      `checkh(ascending33, 33'b0);
      `checkh(implicit65, 65'b0);
      `checkh(typed65, 65'b0);
      `checkh(wire65, 65'b0);
      `checkh(variable65, 65'b0);
      `checkh(ascending65, 65'b0);
      `checkh(implicit95, 95'b0);
      `checkh(typed95, 95'b0);
      `checkh(wire95, 95'b0);
      `checkh(variable95, 95'b0);
      `checkh(ascending95, 95'b0);
      `checkh(implicit129, 129'b0);
      `checkh(typed129, 129'b0);
      `checkh(wire129, 129'b0);
      `checkh(variable129, 129'b0);
      `checkh(ascending129, 129'b0);
`else
      `checkh(implicit_scalar, 1'bz);
      `checkh(variable_scalar, 1'bx);
      `checkh(implicit7, {7{1'bz}});
      `checkh(typed7, {7{1'bz}});
      `checkh(wire7, {7{1'bz}});
      `checkh(variable7, {7{1'bx}});
      `checkh(ascending7, {7{1'bz}});
      `checkh(implicit33, {33{1'bz}});
      `checkh(typed33, {33{1'bz}});
      `checkh(wire33, {33{1'bz}});
      `checkh(variable33, {33{1'bx}});
      `checkh(ascending33, {33{1'bz}});
      `checkh(implicit65, {65{1'bz}});
      `checkh(typed65, {65{1'bz}});
      `checkh(wire65, {65{1'bz}});
      `checkh(variable65, {65{1'bx}});
      `checkh(ascending65, {65{1'bz}});
      `checkh(implicit95, {95{1'bz}});
      `checkh(typed95, {95{1'bz}});
      `checkh(wire95, {95{1'bz}});
      `checkh(variable95, {95{1'bx}});
      `checkh(ascending95, {95{1'bz}});
      `checkh(implicit129, {129{1'bz}});
      `checkh(typed129, {129{1'bz}});
      `checkh(wire129, {129{1'bz}});
      `checkh(variable129, {129{1'bx}});
      `checkh(ascending129, {129{1'bz}});
`endif
      `checkh(primary_variable7, {7{1'bx}});
      `checkh(primary_wire33, {33{1'bz}});
      `checkh(primary_explicit65, {65{1'bx}});
      `checkh(internal_variable7, {7{1'bx}});
      `checkh(internal_wire33, {33{1'bz}});
      `checkh(child_variable65, {65{1'bx}});
      `checkh(child_wire95, {95{1'bz}});
    end
    $display("API initializer checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

/* verilator tracing_off */
module api_internal_defaults (
    output logic [64:0] variable_out,
    output wire logic [94:0] wire_out
);
endmodule
