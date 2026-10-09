// DESCRIPTION: Verilator: Multiple final procedures and immediate termination
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
`ifndef FINAL_MULTI_CASE
`define FINAL_MULTI_CASE 0
`endif

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
`define normal_final(tagv) begin `checkd($time, 1); `checkd(finish_enable, 0); $display("FINALMULTI case=%0d tag=%0d time=%0d", `FINAL_MULTI_CASE, tagv, $time); final_seen++; if (final_seen == 3) $display("*-* All Finished *-*"); end
// verilog_format: on

module finish_leaf #(
  parameter int ID = 0,
  parameter bit STOP = 1
);
  int tail = 0;
  final begin
    `checkd($time, 1);
    `checkd(tail, 0);
    $display("FINALMULTI case=%0d tag=%0d time=%0d", `FINAL_MULTI_CASE, ID, $time);
    if (STOP) begin
      $display("*-* All Finished *-*");
      $finish(0);
      tail = 1;
      $display("UNREACHABLE instance final tail id=%0d", ID);
    end
    else begin
      t.final_seen++;
      if (t.final_seen == 3) $display("*-* All Finished *-*");
    end
  end
endmodule

module t;
  int final_seen = 0;
  bit finish_enable = 0;

  initial begin
    finish_enable = $test$plusargs("ENABLE_FINAL_FINISH");
    #1;
    $display("FINALSTART case=%0d time=%0d", `FINAL_MULTI_CASE, $time);
    $finish(0);
    $display("UNREACHABLE initial final control");
  end

  generate
    if (`FINAL_MULTI_CASE == 0) begin : dual_final
      // Either A or B may execute first. Both terminate, so only one prefix
      // and neither tail are permitted. No final-order assumption is made.
      final begin
        `checkd($time, 1);
        $display("FINALMULTI case=0 tag=A time=%0d", $time);
        $display("*-* All Finished *-*");
        $finish(0);
        $display("UNREACHABLE final A tail");
      end
      final begin
        `checkd($time, 1);
        $display("FINALMULTI case=0 tag=B time=%0d", $time);
        $display("*-* All Finished *-*");
        $finish(0);
        $display("UNREACHABLE final B tail");
      end
    end
    else if (`FINAL_MULTI_CASE == 1) begin : ordinary_final
      // The initial finish has already set gotFinish when all three run.
      final `normal_final(0)
      final `normal_final(1)
      final `normal_final(2)
    end
    else if (`FINAL_MULTI_CASE == 2) begin : untaken_final
      final begin
        if (finish_enable) begin
          $finish(0);
          $display("UNREACHABLE untaken final 0");
        end
        `normal_final(0)
      end
      final begin
        if (finish_enable) begin
          $finish(0);
          $display("UNREACHABLE untaken final 1");
        end
        `normal_final(1)
      end
      final begin
        if (finish_enable) begin
          $finish(0);
          $display("UNREACHABLE untaken final 2");
        end
        `normal_final(2)
      end
    end
    else if (`FINAL_MULTI_CASE == 3) begin : multiple_instances
      finish_leaf #(.ID(0)) a();
      finish_leaf #(.ID(1)) b();
      finish_leaf #(.ID(2)) c();
    end
    else if (`FINAL_MULTI_CASE == 4) begin : generated_finals
      for (genvar index = 0; index < 3; index++) begin : leaf
        final begin
          `checkd($time, 1);
          $display("FINALMULTI case=4 tag=%0d time=%0d", index, $time);
          $display("*-* All Finished *-*");
          $finish(0);
          $display("UNREACHABLE generated final tail id=%0d", index);
        end
      end
    end
    else if (`FINAL_MULTI_CASE == 5) begin : ordinary_instances
      finish_leaf #(.ID(0), .STOP(0)) a();
      finish_leaf #(.ID(1), .STOP(0)) b();
      finish_leaf #(.ID(2), .STOP(0)) c();
    end
  endgenerate
endmodule
