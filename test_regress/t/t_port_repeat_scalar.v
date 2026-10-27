// DESCRIPTION: Verilator: Repeated scalar OUTPUT wire ports
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps
// The default deliberately keeps the raw implicit scalar type.
`ifdef EXPLICIT_SCALAR
`define SCALAR_RANGE [0:0]
`else
`define SCALAR_RANGE
`endif
module scalar_repeat(q, q, d);
  output wire `SCALAR_RANGE q;
  input wire `SCALAR_RANGE d;
  assign q = d;
endmodule
module scalar_unique(input wire `SCALAR_RANGE d, output wire `SCALAR_RANGE q);
  assign q = d;
endmodule
module t(output wire `SCALAR_RANGE a_left, a_right, b_left, b_right, control_out);
  reg `SCALAR_RANGE da, db, dc;
  integer unsigned checks = 0;
  // verilog_format: off
  `define stop $stop
  `define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
  `define CHECK(gotv, expv, labelv) begin `checkh(gotv, expv); $display("PORT_REPEAT_SCALAR_CHECK n=%0d label=%s got=%b", checks, labelv, gotv); end
  // verilog_format: on
  scalar_repeat a(a_left, a_right, da);
  scalar_repeat b(b_left, b_right, db);
  scalar_unique control(dc, control_out);
  initial begin
    da = 1'b0; db = 1'b1; dc = 1'b0;
    #1;
    `CHECK(a_left, 1'b0, "p0_a_left");
    `CHECK(a_right, 1'b0, "p0_a_right");
    `CHECK(b_left, 1'b1, "p0_b_left");
    `CHECK(b_right, 1'b1, "p0_b_right");
    `CHECK(control_out, 1'b0, "p0_unique");
    da = 1'b1; db = 1'b0; dc = 1'b1;
    #1;
    `CHECK(a_left, 1'b1, "p1_a_left");
    `CHECK(a_right, 1'b1, "p1_a_right");
    `CHECK(b_left, 1'b0, "p1_b_left");
    `CHECK(b_right, 1'b0, "p1_b_right");
    `CHECK(control_out, 1'b1, "p1_unique");
    da = 1'bx; db = 1'bz; dc = 1'bx;
    #1;
    `CHECK(a_left, 1'bx, "p2_a_left");
    `CHECK(a_right, 1'bx, "p2_a_right");
    `CHECK(b_left, 1'bz, "p2_b_left");
    `CHECK(b_right, 1'bz, "p2_b_right");
    `CHECK(control_out, 1'bx, "p2_unique");
    da = 1'bz; db = 1'bx; dc = 1'bz;
    #1;
    `CHECK(a_left, 1'bz, "p3_a_left");
    `CHECK(a_right, 1'bz, "p3_a_right");
    `CHECK(b_left, 1'bx, "p3_b_left");
    `CHECK(b_right, 1'bx, "p3_b_right");
    `CHECK(control_out, 1'bz, "p3_unique");
    $display("PORT_REPEAT_SCALAR checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
`undef SCALAR_RANGE
