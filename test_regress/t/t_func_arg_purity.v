// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  bit [31:0] checks = 0;
  bit [31:0] calls = 0;

  function automatic bit bump();
    calls++;
    return 1'b0;
  endfunction

  function automatic bit identity(input bit value);
    return value;
  endfunction

  function automatic bit parity(input bit [6:0] value);
    return ^value;
  endfunction

  initial begin
    for (int phase = 0; phase < 4; phase++) begin
      bit result;
      #1;
      // A constant result cannot discard an effect in the actual argument.
      result = identity(bump()) | 1'b1;
      `checkh(result, 1'b1);
      `checkd(calls, 32'(2 * phase + 1));
      result = parity(7'(phase) ^ {7{bump()}}) | 1'b1;
      `checkh(result, 1'b1);
      `checkd(calls, 32'(2 * phase + 2));
    end
    $display("Actual argument purity checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
