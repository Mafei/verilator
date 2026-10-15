// DESCRIPTION: Verilator: Source finish exits retain compiler line coverage
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  int mode = 0;

  task automatic inline_stop;
    $display("*-* All Finished *-*");  // INLINE_COVER_LINE
    $finish;
  endtask

  task automatic noinline_stop;
    /* verilator no_inline_task */
    $display("*-* All Finished *-*");  // NOINLINE_COVER_LINE
    $finish;
  endtask

  initial begin
    if ($value$plusargs("MODE=%d", mode)) begin
    end
    #1;
    if (mode == 0) begin
      $display("*-* All Finished *-*");  // DIRECT_COVER_LINE
      $finish;
    end
    else if (mode == 1) begin
      inline_stop();  // INLINE_CALL_LINE
    end
    else begin
      noinline_stop();  // NOINLINE_CALL_LINE
    end
    cover (1) $display("UNREACHABLE functional coverage");
    $display("UNREACHABLE source tail");
  end
endmodule
