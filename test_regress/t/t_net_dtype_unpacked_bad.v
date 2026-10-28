// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  typedef struct {
    logic [4:0] four_bits;
    bit [2:0] two_bits;
  } mixed_t;
  // An unpacked aggregate requires each member to be a valid four-state net type.
  wire mixed_t bad_value;
endmodule
