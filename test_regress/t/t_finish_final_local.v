// DESCRIPTION: Verilator: Local exits from a single call-free final body
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
`ifndef FINAL_LOCAL_CASE
`define FINAL_LOCAL_CASE 0
`endif

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  int checks = 0;
  int stop_at = 0;
  int stop_enable = 1;
  int index_value = 0;
  int sum_value = 0;
  int tail = 0;

  initial begin
    if ($value$plusargs("STOP_AT=%d", stop_at)) begin
    end
    if ($value$plusargs("STOP_ENABLE=%d", stop_enable)) begin
    end
    #1;
    $display("INITIAL case=%0d time=%0d", `FINAL_LOCAL_CASE, $time);
    $finish(0);
    $display("UNREACHABLE initial tail");
  end

  // The body declares no locals and calls no task, function or foreign code.
  final begin
    `checkd($time, 1);
    `checkd(tail, 0);
    if (`FINAL_LOCAL_CASE == 0) begin
      $display("NORMAL final checks=%0d time=%0d", checks, $time);
      $display("*-* All Finished *-*");
    end
    else if (`FINAL_LOCAL_CASE == 1) begin
      $display("DIRECT final checks=%0d time=%0d", checks, $time);
      $display("*-* All Finished *-*");
      $finish(0);
      tail = 1;
      $display("UNREACHABLE direct final tail");
    end
    else if (`FINAL_LOCAL_CASE == 2) begin
      // A runtime plusarg keeps the conditional exit from constant folding.
      for (index_value = 0; index_value < 4; index_value++) begin
        sum_value += index_value;
        $display("LOOP index=%0d sum=%0d", index_value, sum_value);
        if (index_value == stop_at) begin
          `checkd(sum_value, 3);
          $display("LOOP final checks=%0d time=%0d", checks, $time);
          $display("*-* All Finished *-*");
          $finish(0);
          tail = 2;
          $display("UNREACHABLE nested final tail");
        end
      end
      tail = 3;
      $display("UNREACHABLE after final loop");
    end
    else if (`FINAL_LOCAL_CASE == 3) begin
      if (stop_enable != 0) begin
        $finish(0);
        $display("UNREACHABLE enabled final tail");
      end
      `checkd(stop_enable, 0);
      $display("UNTAKEN final checks=%0d time=%0d", checks, $time);
      $display("*-* All Finished *-*");
    end
  end
endmodule
