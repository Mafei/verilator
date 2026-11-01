// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); $stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  typedef enum logic [1:0] { CHOICE_A = 2'b01, CHOICE_B = 2'b11 } choice_t;
  logic selector;
  choice_t enum_value;
  choice_t same_value;
  logic [1:0] logic_value;
  bit [1:0] bit_value;
  logic [1:0] want_value;
  bit [1:0] want_bits;
  int checks = 0;

  // Keep the enum type without casts. Unknown selectors merge the differing
  // high bit, while the shared low bit survives both logic and bit storage.
  always_comb begin
    enum_value = selector ? CHOICE_A : CHOICE_B;
    same_value = selector ? CHOICE_A : CHOICE_A;
    logic_value = enum_value;
    bit_value = enum_value;
  end

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    for (int phase = 0; phase < 4; phase++) begin
      case (phase)
        0: begin selector = 1'b0; want_value = 2'b11; want_bits = 2'b11; end
        1: begin selector = 1'b1; want_value = 2'b01; want_bits = 2'b01; end
        2: begin selector = 1'bx; want_value = 2'bx1; want_bits = 2'b01; end
        3: begin selector = 1'bz; want_value = 2'bx1; want_bits = 2'b01; end
        default: $stop;
      endcase
      #1;
      `checkh(enum_value, want_value);
      `checkh(logic_value, want_value);
      `checkh(bit_value, want_bits);
      `checkh(same_value, 2'b01);
      $write("ENUM_COND phase=%0d sel=%b enum=%b logic=%b bit=%b same=%b\n",
             phase, selector, enum_value, logic_value, bit_value, same_value);
      #1;
    end
    if (checks != 16) $stop;
    $write("ENUM_COND_PASS checks=%0d\n", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
