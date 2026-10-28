// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  timeunit 1ns;
  timeprecision 1ns;
  typedef struct packed {
    logic [4:0] four_bits;
    bit [2:0] two_bits;
  } mixed_t;
  typedef mixed_t alias_t;
  typedef struct packed {
    bit [1:0] high_bits;
    bit [2:0] low_bits;
  } bits_t;
  typedef struct packed {
    logic [2:0] four_bits;
    bits_t two_bits;
  } nested_t;
  typedef struct packed {
    logic four_bit;
    bit signed [6:0] two_bits;
  } signed_t;
  logic [7:0] stimulus = 0;
  wire alias_t value;
  wire nested_t nested_value;
  wire mixed_t [2:1] array_value;
  wire signed_t signed_value;
  mixed_t variable_value;
  assign value = stimulus;
  assign nested_value = stimulus;
  assign array_value = {stimulus, ~stimulus};
  assign signed_value = stimulus;
  int checks = 0;
  initial begin
    for (int i = 0; i < 64; i++) begin
      stimulus = 8'(i * 37) ^ 8'ha5;
      #1;
      `checkh(value, stimulus);
      `checkh(value.four_bits, stimulus[7:3]);
      `checkh(value.two_bits, stimulus[2:0]);
      `checkh(nested_value, stimulus);
      `checkh(nested_value.two_bits, stimulus[4:0]);
      `checkh(array_value[2], stimulus);
      `checkh(array_value[1], ~stimulus);
      variable_value = stimulus;
      variable_value.two_bits = 3'(i ^ 5);
      `checkh(variable_value, {stimulus[7:3], 3'(i ^ 5)});
      `checkh(variable_value.two_bits, 3'(i ^ 5));
      `checkh(signed_value.two_bits < 0, $signed(stimulus[6:0]) < 0);
    end
`ifdef EXPECT_FOURSTATE
    stimulus = 8'bxzxx_xzzz;
    #1;
    // The packed vector retains X/Z; reading a two-state member converts them to zero.
    `checkh(value, 8'bxzxx_xzzz);
    `checkh(value.four_bits, 5'bxzxxx);
    `checkh(value.two_bits, 3'b000);
    `checkh(value[2:0], 3'bzzz);
    `checkh(nested_value, 8'bxzxx_xzzz);
    `checkh(nested_value.four_bits, 3'bxzx);
    `checkh(nested_value.two_bits, 5'b00000);
    `checkh(array_value[2], 8'bxzxx_xzzz);
    `checkh(array_value[1], 8'bxxxx_xxxx);
    variable_value = stimulus;
    `checkh(variable_value.two_bits, 3'b000);
    `checkh(variable_value[2:0], 3'bzzz);
    variable_value.two_bits = 3'b101;
    `checkh(variable_value, 8'bxzxx_x101);
    `checkh(variable_value.two_bits, 3'b101);
    `checkh(signed_value.two_bits, 7'b0000000);
    `checkh(signed_value.two_bits < 0, 1'b0);
`endif
    $display("Packed net checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
