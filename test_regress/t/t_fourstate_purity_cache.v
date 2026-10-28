// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  wire done7, done33;
  wire [31:0] checks7, checks33;
  purity_case #(7) c7(done7, checks7);
  purity_case #(33) c33(done33, checks33);
  initial begin
    wait (done7 && done33);
    $display("Purity cache checks: %0d", checks7 + checks33);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module purity_case #(parameter int WIDTH = 7)
    (output bit done = 0, output bit [31:0] checks = 0);
  typedef logic [WIDTH-1:0] word_t;
  word_t data;
  wire word_t result;

  function automatic word_t rotate(input word_t value);
    return {value[WIDTH-2:0], value[WIDTH-1]};
  endfunction

  // Resolution queries the call's purity before its return is lowered to WRITE arguments.
  assign result = rotate(data);
  assign result = 'z;

  task automatic drive_check(input word_t value, input word_t expected);
    data = value;
    #1;
    `checkh(result, expected);
  endtask

  initial begin
    if (WIDTH == 7) begin
      drive_check(word_t'(7'b01xz101), word_t'(7'b1xz1010));
      drive_check('z, 'z);
      drive_check(word_t'(7'b1010010), word_t'(7'b0100101));
      drive_check(word_t'(7'bx10z011), word_t'(7'b10z011x));
    end else begin
      drive_check(word_t'(33'b0_001xz101_001xz101_001xz101_001xz101),
                  word_t'(33'b001xz101_001xz101_001xz101_001xz101_0));
      drive_check('z, 'z);
      drive_check(word_t'(33'b1_01001010_01001010_01001010_01001010),
                  word_t'(33'b01001010_01001010_01001010_01001010_1));
      drive_check(word_t'(33'bx_10z011x1_10z011x1_10z011x1_10z011x1),
                  word_t'(33'b10z011x1_10z011x1_10z011x1_10z011x1_x));
    end
    done = 1;
  end
endmodule
