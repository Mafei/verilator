// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  logic [2:0] value;
  logic [6:0] result;

  always_comb begin
    case (value) inside
      3'b000: result = 7'h10;
      [3'b001:3'b011]: result = 7'h21;
      3'b1??: result = 7'h42;
      default: result = 7'h55;
    endcase
  end

  initial begin
    for (int i = 0; i < 8; i++) begin
      value = 3'(i);
      #1;
      if (i == 0) begin
        `checkh(result, 7'h10);
      end else if (i <= 3) begin
        `checkh(result, 7'h21);
      end else begin
        `checkh(result, 7'h42);
      end
    end
    value = 3'b0xz;
    #1;
    `checkh(result, 7'h55);
    value = 3'b1xz;
    #1;
    `checkh(result, 7'h42);
    value = 3'bx00;
    #1;
    `checkh(result, 7'h55);
    value = 3'bz00;
    #1;
    `checkh(result, 7'h55);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
