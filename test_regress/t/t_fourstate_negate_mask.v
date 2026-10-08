// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks = checks + 1; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  bit clk = 0;
  always #5 clk = ~clk;
  int unsigned checks = 0;
  int unsigned cycle = 0;
  int unsigned calls = 0;
  logic signed [64:0] data;
  bit unknown_result;

  function automatic logic signed [64:0] once_value();
    calls = calls + 1;
    return data;
  endfunction

  always @(posedge clk) begin
    cycle = cycle + 1;
    data = 65'(cycle * 13);
    calls = 0;
    // The X/Z visitor must execute the operand once even without a value consumer.
    // This test is vlt-only because Icarus 12 misreports inline $isunknown(-f())
    // on a known return value; the portable negate test checks the same arithmetic.
    unknown_result = $isunknown(-once_value());
    `checkh(unknown_result, 1'b0);
    `checkh(calls, 32'd1);
    data[64] = 1'bx;
    calls = 0;
    unknown_result = $isunknown(-once_value());
    `checkh(unknown_result, 1'b1);
    `checkh(calls, 32'd1);
    data[64] = 1'bz;
    calls = 0;
    unknown_result = $isunknown(-once_value());
    `checkh(unknown_result, 1'b1);
    `checkh(calls, 32'd1);
    if (cycle == 37) begin
      $display("Negate mask checks: %0d", checks);
      $write("*-* All Finished *-*\n");
      $finish;
    end
  end
endmodule
