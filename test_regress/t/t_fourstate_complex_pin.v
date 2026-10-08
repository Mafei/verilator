// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module y(input logic [6:0] x, output wire [6:0] result);
  assign result = x;
endmodule

module y_bit(input bit [6:0] x, output wire [6:0] result);
  assign result = x;
endmodule

module t;
  typedef bit [6:0] bitword_t;
  bit [6:0] two_state;
  logic [14:0] x;
  wire [6:0] selected;
  wire [6:0] inverted;
  wire [6:0] casted;
  wire [6:0] known;
  y h(x[9:3], selected);
  y h_not(~x[9:3], inverted);
  y_bit h_bit(bitword_t'(x[9:3]), casted);
  y h_known(~two_state, known);

  initial begin
    x = 15'h18;
    two_state = 7'h18;
    #1;
    `checkh(selected, 7'h03);
    `checkh(inverted, 7'h7c);
    `checkh(casted, 7'h03);
    `checkh(known, 7'h67);
    x[9:3] = 7'bxz101zx;
    #1;
    `checkh(selected, 7'bxz101zx);
    `checkh(inverted, 7'bxx010xx);
    `checkh(casted, 7'b0010100);
    for (int i = 0; i < 4; i++) begin
      x[9:3] = 7'(i);
      two_state = 7'(i);
      #1;
      `checkh(selected, 7'(i));
      `checkh(inverted, ~7'(i));
      `checkh(casted, 7'(i));
      `checkh(known, ~7'(i));
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
