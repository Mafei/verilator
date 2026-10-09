// DESCRIPTION: Verilator: Finish propagation across separate task calls
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
`ifndef FINISH_CALL_CASE
`define FINISH_CALL_CASE 0
`endif

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  logic q = 1'b0;
  int output_value = 19;
  int inout_value = 23;
  int caller_done = 0;
  int finish_enable = 1;

  // Only locals and formal arguments are accessed in separate tasks. Module
  // variable access would hit the existing IMPURE boundary, not this defect.
  task automatic stop_plain;
    /*verilator no_inline_task*/
`ifdef FINISH_CALL_TIMED
    #1;
`endif
    $display("CALLENTER case=%0d kind=plain time=%0d", `FINISH_CALL_CASE, $time);
    $finish(0);
    $display("UNREACHABLE plain callee");
  endtask

  task automatic outer_plain;
    /*verilator no_inline_task*/
    $display("CALLOUTER case=%0d kind=plain time=%0d", `FINISH_CALL_CASE, $time);
    stop_plain();
    $display("UNREACHABLE plain outer caller");
  endtask

  task automatic stop_params(input int enable, output int output_formal,
                             inout int inout_formal);
    /*verilator no_inline_task*/
    output_formal = 72;
    inout_formal = 84;
`ifdef FINISH_CALL_TIMED
    #1;
`endif
    `checkd(output_formal, 72);
    `checkd(inout_formal, 84);
    $display("CALLENTER case=%0d kind=params time=%0d enable=%0d output=%0d inout=%0d",
             `FINISH_CALL_CASE, $time, enable, output_formal, inout_formal);
    if (enable != 0) begin
      $finish(0);
      output_formal = 99;
      inout_formal = 101;
      $display("UNREACHABLE params callee");
    end
    $display("CALLRETURN case=%0d kind=params time=%0d output=%0d inout=%0d",
             `FINISH_CALL_CASE, $time, output_formal, inout_formal);
  endtask

  task automatic outer_params(input int enable, output int output_formal,
                              inout int inout_formal);
    /*verilator no_inline_task*/
    output_formal = 41;
    inout_formal = 43;
    $display("CALLOUTER case=%0d kind=params time=%0d enable=%0d output=%0d inout=%0d",
             `FINISH_CALL_CASE, $time, enable, output_formal, inout_formal);
    stop_params(enable, output_formal, inout_formal);
    if (enable != 0) $display("UNREACHABLE params outer caller");
    $display("CALLOUTERRETURN case=%0d time=%0d output=%0d inout=%0d",
             `FINISH_CALL_CASE, $time, output_formal, inout_formal);
  endtask

  initial begin
    finish_enable = int'(!$test$plusargs("DISABLE_TASK_FINISH"));
    $display("CALLSTART case=%0d time=%0d", `FINISH_CALL_CASE, $time);
    if (`FINISH_CALL_CASE == 0 || `FINISH_CALL_CASE == 1) stop_plain();
    else if (`FINISH_CALL_CASE == 2) outer_plain();
    else if (`FINISH_CALL_CASE == 6 || `FINISH_CALL_CASE == 7)
      outer_params(finish_enable, output_value, inout_value);
    else stop_params(finish_enable, output_value, inout_value);
    if (`FINISH_CALL_CASE == 5 || `FINISH_CALL_CASE == 7) begin
      `checkd(finish_enable, 0);
      `checkd(output_value, 72);
      `checkd(inout_value, 84);
      caller_done++;
      $display("CALLCALLER case=%0d time=%0d output=%0d inout=%0d done=%0d",
               `FINISH_CALL_CASE, $time, output_value, inout_value, caller_done);
      $finish(0);
      $display("UNREACHABLE control initial tail");
    end
    else begin
      caller_done = 9;
      $display("UNREACHABLE source caller");
    end
  end

  final begin
    `checkd(q, 1'b0);
    `checkd(caller_done, (`FINISH_CALL_CASE == 5 || `FINISH_CALL_CASE == 7) ? 1 : 0);
    `checkd(output_value, (`FINISH_CALL_CASE == 5 || `FINISH_CALL_CASE == 7) ? 72 : 19);
    `checkd(inout_value, (`FINISH_CALL_CASE == 5 || `FINISH_CALL_CASE == 7) ? 84 : 23);
`ifdef FINISH_CALL_TIMED
    `checkd($time, 1);
`else
    `checkd($time, 0);
`endif
    $display("CALLFINAL case=%0d time=%0d output=%0d inout=%0d done=%0d q=%b",
             `FINISH_CALL_CASE, $time, output_value, inout_value, caller_done, q);
    $display("*-* All Finished *-*");
  end
endmodule
