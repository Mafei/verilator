// DESCRIPTION: Verilator: Current-process termination after $finish
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
`ifndef FINISH_CASE
`define FINISH_CASE 0
`endif

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define before_finish $display("BEFORE case=%0d time=%0d entered=%0d", `FINISH_CASE, $time, entered)
// verilog_format: on

module t;
  int checks = 0;
  int seed = 11;
  int entered = 0;
  int tail = 0;
  int output_value = 19;
  int inout_value = 23;
  int function_result = 29;
  int function_calls = 0;
  int next_calls = 0;
  int loop_sum = 0;
  bit clk = 0;

  task automatic inner_stop(output int output_formal, inout int inout_formal);
    entered++;
    output_formal = seed + 61;
    inout_formal = seed + 73;
    `checkd(output_formal, 72);
    `checkd(inout_formal, 84);
    $display("PARAMS output=%0d inout=%0d", output_formal, inout_formal);
    `before_finish;
    $finish(0);
    tail = 1;
    $display("UNREACHABLE inner task");
  endtask

  task automatic outer_stop(output int output_formal, inout int inout_formal);
    output_formal = seed + 31;
    inout_formal = seed + 43;
    inner_stop(output_formal, inout_formal);
    tail = 2;
    $display("UNREACHABLE outer task");
  endtask

  function automatic int stop_value(input int value);
    entered++;
    function_calls++;
    `checkd(value, 11);
    `before_finish;
    $finish(0);
    tail = 1;
    $display("UNREACHABLE function body");
    return value + 17;
  endfunction

  function automatic int next_value;
    next_calls++;
    return seed + 37;
  endfunction

  generate
    if (`FINISH_CASE == 0) begin : direct_case
      initial begin
        entered++;
        `before_finish;
        $finish(0);
        $display("UNREACHABLE direct initial");
      end
    end
    else if (`FINISH_CASE == 1) begin : loop_case
      initial begin
        for (int outer = 0; outer < 3; outer++) begin
          for (int inner = 0; inner < 3; inner++) begin
            entered++;
            if (outer == seed - 10 && inner == 1) begin
              `before_finish;
              $finish(0);
              tail = 1;
              $display("UNREACHABLE nested loop");
            end
            loop_sum += outer * 3 + inner;
          end
        end
        tail = 2;
        $display("UNREACHABLE after loops");
      end
    end
    else if (`FINISH_CASE == 2) begin : timed_case
      initial begin
        #3;
        entered++;
        `before_finish;
        $finish(0);
        $display("UNREACHABLE timed initial");
      end
    end
    else if (`FINISH_CASE == 3) begin : task_case
      initial begin
        outer_stop(output_value, inout_value);
        tail = 3;
        $display("UNREACHABLE task caller");
      end
    end
    else if (`FINISH_CASE == 4) begin : function_case
      initial begin
        function_result = stop_value(seed);
        function_result = next_value();
        tail = 2;
        $display("UNREACHABLE function caller");
      end
    end
    else if (`FINISH_CASE == 5) begin : always_case
      initial begin
        #2;
        clk = 1;
      end
      always @(posedge clk) begin
        entered++;
        `before_finish;
        $finish(0);
        $display("UNREACHABLE always activation");
      end
    end
  endgenerate

  final begin
    `checkd(entered, `FINISH_CASE == 1 ? 5 : 1);
    `checkd(tail, 0);
    `checkd(output_value, 19);
    `checkd(inout_value, 23);
    `checkd(function_result, 29);
    `checkd(function_calls, `FINISH_CASE == 4 ? 1 : 0);
    `checkd(next_calls, 0);
    `checkd(loop_sum, `FINISH_CASE == 1 ? 6 : 0);
    `checkd($time, `FINISH_CASE == 2 ? 3 : (`FINISH_CASE == 5 ? 2 : 0));
    $display(
        "FINAL case=%0d checks=%0d entered=%0d output=%0d inout=%0d result=%0d calls=%0d next=%0d sum=%0d",
        `FINISH_CASE, checks, entered, output_value, inout_value, function_result, function_calls,
        next_calls, loop_sum);
    $display("*-* All Finished *-*");
  end
endmodule
