// DESCRIPTION: Verilator: Preserve diagnostics before index carry arithmetic
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t (
    input logic [94:0] data,
    input logic [3:0][7:0] packed_bytes,
    input logic [3:0] i4,
    input logic [63:0] i64,
    output wire [2:0] direct4, minus4, shifted4,
    output wire [2:0] direct64, minus64, shifted64, constant4,
    output wire [7:0] packed4, packed64
);
  wire [98:4] shifted = data;
  // The original diagnostic expands the direct narrow index.
  assign direct4 = data[i4+:3];
  // Nonconstant range subtraction previously used 32-bit arithmetic and its exemption.
  assign minus4 = data[i4-:3];
  assign shifted4 = shifted[i4+:3];
  // The original wide index diagnostics report 64, without generated carry bits.
  assign direct64 = data[i64+:3];
  assign minus64 = data[i64-:3];
  assign shifted64 = shifted[i64+:3];
  // Packed element scaling previously used 32-bit arithmetic and its exemption.
  assign packed4 = packed_bytes[i4];
  assign packed64 = packed_bytes[i64];
  // The original constant range fold kept its sized 4-bit result.
  assign constant4 = shifted[4'h4+:3];
endmodule
