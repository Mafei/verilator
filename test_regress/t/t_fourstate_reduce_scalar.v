// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define check_scalar(gotv,expv) begin `checkh(&(gotv),expv); `checkh(|(gotv),expv); `checkh(^(gotv),expv); `checkh(~&(gotv),~(expv)); `checkh(~|(gotv),~(expv)); `checkh(~^(gotv),~(expv)); end
`define check_vector(gotv,andv,orv,xorv) begin `checkh(&(gotv),andv); `checkh(|(gotv),orv); `checkh(^(gotv),xorv); `checkh(~&(gotv),~(andv)); `checkh(~|(gotv),~(orv)); `checkh(~^(gotv),~(xorv)); end
`define check_ops(gotv,expv) begin `checkh(gotv[5],expv); `checkh(gotv[4],expv); `checkh(gotv[3],expv); `checkh(gotv[2],~(expv)); `checkh(gotv[1],~(expv)); `checkh(gotv[0],~(expv)); end
// verilog_format: on

module t;
  typedef logic scalar_t;
  typedef logic signed signed_scalar_t;
  typedef logic [9:3] vector_t;
  typedef struct packed {logic flag; logic [2:0] pad;} record_t;
  localparam logic CONSTANT_Z = 1'bz;
  scalar_t scalar;
  scalar_t typed_unsigned;
  signed_scalar_t typed_signed;
  logic memory[3:1];
  record_t record_value;
  record_t records[3:1];
  logic [14:8] container;
  logic [3:3] one_offset;
  logic [0:0] one_zero;
  logic [6:0] vector_unsigned;
  logic signed [6:0] vector_signed;
  vector_t vector_offset;
  bit two_unsigned;
  bit signed two_signed;
  logic normal_expected;
  logic bit_expected;
  logic and_expected, or_expected, xor_expected;
  logic [5:0] port_ops;
  int index;
  int phase;
  int calls = 0;
  int checks = 0;

  scalar_reduce_port port_instance(scalar, port_ops);

  function automatic logic sample_scalar;
    calls++;
    return scalar;
  endfunction
  function automatic logic identity_scalar(input logic value);
    return value;
  endfunction

  initial begin
    // Constants already have defined four-state folding; retain adjacent controls.
    `check_scalar(1'b0, 1'b0);
    `check_scalar(1'b1, 1'b1);
    `check_scalar(1'bx, 1'bx);
    `check_scalar(1'bz, 1'bx);
    `check_scalar(CONSTANT_Z, 1'bx);
    for (phase = 0; phase < 8; phase++) begin
      case (phase % 4)
        0: begin scalar = 1'bz; normal_expected = 1'bx; bit_expected = 0; end
        1: begin scalar = 1'b0; normal_expected = 1'b0; bit_expected = 0; end
        2: begin scalar = 1'bx; normal_expected = 1'bx; bit_expected = 0; end
        default: begin scalar = 1'b1; normal_expected = 1'b1; bit_expected = 1; end
      endcase
      case (phase)
        0: begin vector_unsigned = 7'bzzzzzzz; and_expected = 1'bx; or_expected = 1'bx; xor_expected = 1'bx; end
        1: begin vector_unsigned = 7'b0000000; and_expected = 1'b0; or_expected = 1'b0; xor_expected = 1'b0; end
        2: begin vector_unsigned = 7'b1111111; and_expected = 1'b1; or_expected = 1'b1; xor_expected = 1'b1; end
        3: begin vector_unsigned = 7'b0101010; and_expected = 1'b0; or_expected = 1'b1; xor_expected = 1'b1; end
        4: begin vector_unsigned = 7'b0zzzzzz; and_expected = 1'b0; or_expected = 1'bx; xor_expected = 1'bx; end
        5: begin vector_unsigned = 7'b1zzzzzz; and_expected = 1'bx; or_expected = 1'b1; xor_expected = 1'bx; end
        6: begin vector_unsigned = 7'b01x0101; and_expected = 1'b0; or_expected = 1'b1; xor_expected = 1'bx; end
        default: begin vector_unsigned = 7'b1010101; and_expected = 1'b0; or_expected = 1'b1; xor_expected = 1'b0; end
      endcase
      index = (phase % 3) + 1;
      typed_unsigned = scalar;
      typed_signed = scalar;
      memory[index] = scalar;
      container = 0;
      container[10] = scalar;
      record_value = 0;
      record_value.flag = scalar;
      records[index] = record_value;
      one_offset[3] = scalar;
      one_zero[0] = scalar;
      vector_signed = vector_unsigned;
      vector_offset = vector_unsigned;
      two_unsigned = scalar;
      two_signed = scalar;
      #1;
      `check_scalar(scalar, normal_expected);
      `check_scalar(typed_unsigned, normal_expected);
      `check_scalar(typed_signed, normal_expected);
      `check_scalar(memory[index], normal_expected);
      `check_scalar(container[10], normal_expected);
      `check_scalar(container[10:10], normal_expected);
      `check_scalar({scalar}, normal_expected);
      `check_scalar(record_value.flag, normal_expected);
      `check_scalar(one_offset[3], normal_expected);
      `check_scalar(sample_scalar(), normal_expected);
      `check_scalar(one_zero[0], normal_expected);
      `check_scalar($unsigned(scalar), normal_expected);
      `check_scalar($signed(scalar), normal_expected);
      `check_scalar(records[index].flag, normal_expected);
      `check_ops(port_ops, normal_expected);
      `check_scalar(identity_scalar(scalar), normal_expected);
      `check_scalar({memory[index]}, normal_expected);
      `checkd(calls, (phase + 1) * 6);
      `check_scalar(two_unsigned, bit_expected);
      `check_scalar(two_signed, bit_expected);
      `check_vector(vector_unsigned, and_expected, or_expected, xor_expected);
      `check_vector(vector_signed, and_expected, or_expected, xor_expected);
      `check_vector(vector_offset, and_expected, or_expected, xor_expected);
    end
    $display("Scalar reduction checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module scalar_reduce_port(input logic value, output logic [5:0] ops);
  always_comb ops = {&value, |value, ^value, ~&value, ~|value, ~^value};
endmodule
