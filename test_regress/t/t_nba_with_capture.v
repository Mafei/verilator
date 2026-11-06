// DESCRIPTION: Verilator: Capture an impure reduction index exactly once
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t (
    input bit clk,
    input bit [30:0] payload,
    output bit [31:0] calls,
    output bit [30:0] target0,
    output bit [30:0] target1
);
  int ones[1] = '{1};
  bit [30:0] target[2];

  function automatic int next_index(int item_value);
    calls++;
    // Successive calls select 0, 1, 0, 1. A duplicate call is observable in
    // both this blocking counter and the element receiving the pending NBA.
    return int'((calls - 1) & item_value);
  endfunction

  initial begin
    calls = 0;
    target[0] = 0;
    target[1] = 0;
  end
  always @(posedge clk) target[ones.sum() with (next_index(item))] <= payload;
  assign target0 = target[0];
  assign target1 = target[1];
endmodule
