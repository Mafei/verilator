// DESCRIPTION: Verilator: Do not retain padding from a clipped constant select
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t (
    input bit [1:0] mode,
    input bit [61:0] seed,
    input bit route,
    output bit exact_ok,
    output bit other_ok
);
  logic [62:0] bank[2];
  logic [62:0] expected;
  logic [62:0] other;
  logic [1:0] rhs;

  initial begin
    bank[0] = {1'b0, seed};
    other = ~{1'b0, seed};
    bank[1] = other;
    case (mode)
      0: rhs = 2'b11;  // Known data control: bit63 must be discarded.
      1: rhs = 2'b1x;  // Value channel padding would differ although displays match.
      2: rhs = 2'bz1;  // An XZ-only padding bit must also be discarded.
      3: rhs = 2'b01;  // No high-source-bit control.
    endcase
    expected = {rhs[0], seed};
    // Only bit62 of this selection overlaps the declared destination.
    // verilator lint_off SELRANGE
    bank[route][63:62] <= rhs;
    // verilator lint_on SELRANGE
    rhs = 0;
  end
  assign exact_ok = bank[0] === expected;
  assign other_ok = bank[1] === other;
endmodule
