// DESCRIPTION: Verilator: Packed indices use element widths in diagnostics
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t (
    input logic [3:0][7:0] p8,
    input logic [2:0][6:0] p7,
    input logic [2:0][32:0] p33,
    input logic [1:0][2:0][6:0] p3d,
    input logic [1:0] i2,
    input logic [2:0] i3,
    input logic i1,
    input logic signed [3:0] signed_i4,
    input logic [7:0] words [1:3],
    output wire [7:0] signed_word,
    output wire [7:0] byte_read,
    output wire [15:0] byte_plus,
    output wire [15:0] byte_minus,
    output wire [7:0] shifted_read,
    output wire [7:0] ascending_read,
    output wire [6:0] seven_read,
    output wire [32:0] word_read,
    output wire [6:0] nested_read
);
  wire [5:2][7:0] shifted = p8;
  // The ascending declaration exercises reversed element normalization.
  // verilator lint_off ASCRANGE
  wire [0:3][7:0] ascending = p8;
  // verilator lint_on ASCRANGE

  // Generated declaration-offset subtraction must retain an unsized signed constant.
  assign signed_word = words[signed_i4];

  // Address widths depend on the declared element range, not element bit width.
  assign byte_read = p8[i2];
  assign byte_plus = p8[i2+:2];
  assign byte_minus = p8[i2-:2];
  assign shifted_read = shifted[i3];
  assign ascending_read = ascending[i2];
  assign seven_read = p7[i2];
  assign word_read = p33[i2];
  assign nested_read = p3d[i1][i2];
endmodule
