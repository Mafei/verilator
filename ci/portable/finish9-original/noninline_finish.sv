// DESCRIPTION: Independent timed no-inline task termination and caller control
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps / 1ps
module t;
  logic q;
  task automatic stop_now;
    /*verilator no_inline_task*/
    #1;
    $display("OBS 9 callee_before %0d", $time);
    $finish;
    $display("UNREACHABLE independent_callee");
  endtask
  initial begin
    q = 1'b0;
    $dumpfile("wave.vcd");
    $dumpvars(0, q);
    stop_now();
    $display("UNREACHABLE independent_caller");
  end
  final $display("FINAL 9 %0d q=%b", $time, q);
endmodule
