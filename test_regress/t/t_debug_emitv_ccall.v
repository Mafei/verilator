// DESCRIPTION: Verilator: Debug CCall argument boundaries and DPI bindings
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d exp=%0d (%s !== %s)\n", `__FILE__, `__LINE__, (gotv), (expv), `"gotv`", `"expv`"); `stop; end checks++; end while (0);
// verilog_format: on

module t;
  import "DPI-C" function int ccall_seed(input int index);
  import "DPI-C" function int ccall_pair(
    input int first,
    input int second
  );
  import "DPI-C" context function int ccall_context_pair(
    input int first,
    input int second
  );
  import "DPI-C" function int ccall_context_ok();
  import "DPI-C" function int ccall_context_count();
  import "DPI-C" function int ccall_single(input int value);
  import "DPI-C" function int ccall_empty();
  import "DPI-C" task ccall_empty_task();
  import "DPI-C" function int ccall_empty_count();

  int left;
  int right;
  int result;
  int checks = 0;
  initial begin
    // The imported seed is impure, so the compiler must preserve runtime calls.
    // Bounded signed values exercise both argument orders without overflow.
    for (int step = 0; step < 32; step++) begin
      left = ccall_seed(step);
      right = ccall_seed(step + 53);
      `checkd(left, ((step * 37) % 251) - 125);
      `checkd(right, (((step + 53) * 37) % 251) - 125);
      result = ccall_pair(left, right);
      `checkd(result, left * 101 + right);
      result = ccall_pair(right, left);
      `checkd(result, right * 101 + left);
      begin : nested_context
        result = ccall_context_pair(left, right);
        `checkd(result, left * 103 - right);
        `checkd(ccall_context_ok(), 1);
      end
      result = ccall_single(left);
      `checkd(result, left - 19);
      result = ccall_empty();
      `checkd(result, 17);
      ccall_empty_task();
    end
    `checkd(ccall_context_count(), 32);
    `checkd(ccall_empty_count(), 32);
    $display("EmitV CCall runtime checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
