// DESCRIPTION: Verilator: Trace writes after a split coroutine resumes
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d exp=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while(0)
`define STRINGIFY_(x) `"x`"
`define STRINGIFY(x) `STRINGIFY_(x)
// verilog_format: on

module child(output bit done);
  int phase;
  int value_a;
  int value_b;
  initial begin
    done = 0;
    phase = 0;
    value_a = 0;
    value_b = 0;
    #1;
    phase = 1;
    value_a = 7;
    value_b = 19;
    done = 1;
  end
endmodule

module t;
  bit [1:0] done;
  child u0(.done(done[0]));
  child u1(.done(done[1]));
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #2;
    `checkd(done, 2'b11);
    `checkd(u0.done, 1'b1);
    `checkd(u1.done, 1'b1);
    `checkd(u0.phase, 1);
    `checkd(u1.phase, 1);
    `checkd(u0.value_a, 7);
    `checkd(u1.value_a, 7);
    `checkd(u0.value_b, 19);
    `checkd(u1.value_b, 19);
    $display("TRACE_MODEL_PASS done=%b", done);
    $display("Trace resume checkpoints: 9");
    $write("*-* All Finished *-*\n");
    #1;
    $finish;
  end
endmodule
