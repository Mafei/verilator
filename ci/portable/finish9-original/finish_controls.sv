// DESCRIPTION: Independent bounded simulation-termination controls
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
`ifndef CASE
`define CASE 0
`endif

// verilog_format: off
`define start q = 1'b0; $dumpfile("wave.vcd"); $dumpvars(0, q)
`define before_finish $display("OBS %0d before %0d", `CASE, $time)
// verilog_format: on

module t;
  logic q;
  int result_value;

`ifdef FINISH_TASK
  task automatic stop_now;
    `before_finish;
    $finish;
    $display("UNREACHABLE task_body");
  endtask
`endif

`ifdef FINISH_FUNCTION
  function automatic int stop_value(input int value);
    `before_finish;
    $finish;
    $display("UNREACHABLE function_body");
    return value + 1;
  endfunction
`endif

  initial begin
    `start;
    case (`CASE)
      0: begin
        `before_finish;
        $finish;
        $display("UNREACHABLE initial_body");
      end
      1: begin
        #1;
        `before_finish;
        $finish;
        $display("UNREACHABLE coroutine_body");
        #1;
        $display("UNREACHABLE coroutine_future");
      end
`ifdef FINISH_TASK
      2: begin
        #1;
        stop_now();
        $display("UNREACHABLE task_caller");
      end
`endif
`ifdef FINISH_FUNCTION
      3: begin
        #1;
        result_value = stop_value(7);
        $display("UNREACHABLE function_caller result=%0d", result_value);
      end
`endif
      4: begin
        fork
          begin
            #1;
            `before_finish;
            $finish;
            $display("UNREACHABLE fork_child");
          end
          begin
            #3;
            $display("UNREACHABLE fork_future");
          end
        join
        $display("UNREACHABLE fork_join_caller");
      end
      5: begin
        #1;
        q <= 1'b1;
        $strobe("UNREACHABLE postponed_strobe");
        `before_finish;
        $finish;
        $display("UNREACHABLE nba_same_process");
      end
      6: begin
        fork
          begin
            #1;
            #0;
            $display("UNREACHABLE inactive_resume");
          end
          begin
            #1;
            `before_finish;
            $finish;
            $display("UNREACHABLE inactive_finisher");
          end
          begin
            #2;
            $display("UNREACHABLE inactive_future");
          end
        join
        $display("UNREACHABLE inactive_join_caller");
      end
      7: begin
        #1;
        `before_finish;
        $finish;
        $display("UNREACHABLE final_control_initial");
      end
      default: begin
        $display("UNREACHABLE invalid_configuration");
        $finish;
      end
    endcase
  end

`ifndef FINAL_STOP
  final begin
    $display("FINAL %0d %0d q=%b", `CASE, $time, q);
  end
`else
  // Either final may run first. Both finish, so only one prefix is permitted.
  final begin
    $display("FINAL %0d A %0d q=%b", `CASE, $time, q);
    $finish;
    $display("UNREACHABLE final_A_tail");
  end
  final begin
    $display("FINAL %0d B %0d q=%b", `CASE, $time, q);
    $finish;
    $display("UNREACHABLE final_B_tail");
  end
`endif
endmodule
