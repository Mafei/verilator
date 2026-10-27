// DESCRIPTION: Verilator: Static ancestor task instance context and known-bit state checks
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module state_leaf(output reg [7:0] first, second);
  initial begin
    #1; emit(8'h01, first);
    #1; emit(8'h02, second);
  end
endmodule
module through_mid(output wire [7:0] first, second);
  state_leaf leaf(first, second);
endmodule
module nearest_mid(output wire [7:0] first, second);
  integer calls = 0;
  task emit(input [7:0] token, output [7:0] value);
    calls = calls + 1;
    value = 8'hc0 | token;
  endtask
  state_leaf leaf(first, second);
endmodule
module state_parent_a(output wire [7:0] first, second, near_first, near_second);
  integer calls = 0;
  task emit(input [7:0] token, output [7:0] value);
    calls = calls + 1;
    value = 8'ha0 | token;
  endtask
  through_mid bridge(first, second);
  nearest_mid near0(near_first, near_second);
endmodule
module state_parent_b(output wire [7:0] first, second);
  integer calls = 0;
  task emit(input [7:0] token, output [7:0] value);
    calls = calls + 1;
    value = 8'hb0 | token;
  endtask
  through_mid bridge(first, second);
endmodule
module t;
  integer checks = 0;
  `define CHECK(actual, expected, label) \
    begin \
      checks = checks + 1; \
      if ((actual) !== (expected)) $fatal(1, label); \
      $display("ANCESTOR_CHECK n=%0d label=%s got=%0h", checks, label, actual); \
    end
  wire [7:0] a0, a1, n0, n1, a2, a3, n2, n3, b0, b1;
  state_parent_a a(a0, a1, n0, n1);
  state_parent_a aa(a2, a3, n2, n3);
  state_parent_b b(b0, b1);
  initial begin
    #3;
    `CHECK(a0, 8'ha1, "a_first")
    `CHECK(a1, 8'ha2, "a_second")
    `CHECK(a2, 8'ha1, "aa_first")
    `CHECK(a3, 8'ha2, "aa_second")
    `CHECK(b0, 8'hb1, "b_first")
    `CHECK(b1, 8'hb2, "b_second")
    `CHECK(n0, 8'hc1, "a_nearest_first")
    `CHECK(n1, 8'hc2, "a_nearest_second")
    `CHECK(n2, 8'hc1, "aa_nearest_first")
    `CHECK(n3, 8'hc2, "aa_nearest_second")
    `CHECK(a.calls, 2, "a_state")
    `CHECK(aa.calls, 2, "aa_independent_state")
    `CHECK(b.calls, 2, "b_state")
    `CHECK(a.near0.calls, 2, "a_nearest_state")
    `CHECK(aa.near0.calls, 2, "aa_nearest_state")
    if (checks != 15) $fatal(1, "missing checks");
    $display("ANCESTOR_STATE checks=%0d", checks);
    `undef CHECK
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
