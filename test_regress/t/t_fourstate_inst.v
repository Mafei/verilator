// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2007 Wilson Snyder
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  supply0 [1:0] low;
  supply1 [1:0] high;
  logic [6:0] isizedwire;
  logic ionewire;
  wire [6:0] osizedreg;
  wire oonewire;

  t_inst sub (
    .osizedreg,
    .oonewire,
    .isizedwire(isizedwire[6:0]),
    .*
  );

  initial begin
    for (int i = 0; i < 8; i++) begin
      case (i % 4)
        0: begin
          isizedwire = 7'(i * 13 + 3);
          ionewire = 1'b0;
        end
        1: begin
          isizedwire = 7'b10xz010;
          ionewire = 1'bx;
        end
        2: begin
          isizedwire = 'x;
          ionewire = 1'bz;
        end
        3: begin
          isizedwire = 'z;
          ionewire = 1'b1;
        end
      endcase
      #1;
      `checkh(low, 2'b00);
      `checkh(high, 2'b11);
      `checkh(osizedreg, isizedwire);
      `checkh(oonewire, ionewire);
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module t_inst (
  output logic [6:0] osizedreg,
  output wire oonewire,
  input logic [6:0] isizedwire,
  input wire ionewire
);
  assign oonewire = ionewire;
  always_comb osizedreg = isizedwire;
endmodule
