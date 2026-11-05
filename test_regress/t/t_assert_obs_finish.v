// DESCRIPTION: Verilator: Finish inside an observed assertion action
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns / 1ps
module t;
  task automatic finish_action();
`ifdef OBS_FINISH_NOINLINE
    /* verilator no_inline_task */
`endif
    $display("OBS_FINISH_ENTER");
    $finish;
    $display("OBS_FINISH_LATE_IN_ACTION");
  endtask
  task automatic other_action();
    $display("OBS_FINISH_OTHER_ACTION");
  endtask
  initial begin
    assert #0 (1) finish_action();
    assert #0 (1) other_action();
  end
  final begin
    $display("OBS_FINISH_FINAL");
    $write("*-* All Finished *-*\n");
  end
endmodule
