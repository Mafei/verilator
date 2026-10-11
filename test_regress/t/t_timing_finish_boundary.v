// DESCRIPTION: Verilator: Immediate finish across NBA and inactive boundaries
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
`ifndef FINISH_BOUNDARY_CASE
`define FINISH_BOUNDARY_CASE 0
`endif

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define queue_update q <= 1; word7 <= 7'(seed); word65 <= (65'(seed) << 33)
`define before_finish $display("BEFORE case=%0d time=%0d q=%0d", `FINISH_BOUNDARY_CASE, $time, q)
`define STRINGIFY_(x) `"x`"
`define STRINGIFY(x) `STRINGIFY_(x)
// verilog_format: on

module t;
  bit q = 0;
  logic [6:0] word7 = '0;
  logic [64:0] word65 = '0;
  bit armed = 0;
  int seed = 17;
  int checks = 0;
  int entered = 0;
  int tail = 0;
  int final_calls = 0;
  int inactive_entered = 0;
  int inactive_done = 0;
  int function_result = 41;

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
  end

  task automatic stop_inner;
    entered++;
    `before_finish;
    $finish(0);
    tail++;
    $display("BAD task tail");
  endtask

  task automatic stop_outer;
    stop_inner();
    tail++;
    $display("BAD outer task tail");
  endtask

  function automatic int ref_stop_value(input bit enable, input int value);
    // Set the function's return variable before finish. An automatic ref
    // target in an outlined caller must not alias this temporary return value.
    ref_stop_value = value - 3;
    if (enable) $finish(0);
    $display("NORMAL ref value=%0d", value);
  endfunction

  task automatic ref_owner(ref int target, input bit enable, input int value);
    // verilator no_inline_task
    target = ref_stop_value(enable, value);
    if (enable) $display("BAD ref owner tail");
    else $display("NORMAL ref owner target=%0d", target);
  endtask

  function automatic int stop_noinline_function(input int value, input bit enable);
    // verilator no_inline_task
    stop_noinline_function = value - 3;
    if (enable) $finish(0);
    $display("BAD noninline function tail");
    return value + 11;
  endfunction

  function automatic int normal_value(input int value);
    tail++;
    return value + 11;
  endfunction

  function automatic int normal_noinline_value(input int value);
    // verilator no_inline_task
    $display("NORMAL noninline value=%0d", value);
    return value + 11;
  endfunction

  task automatic stop_timed;
    #1;
    seed += 3;
    `queue_update;
    $strobe("BAD postponed case=%0d q=%0d", `FINISH_BOUNDARY_CASE, q);
    #0;
    `checkd(q, 0);
    entered++;
    `before_finish;
    $finish(0);
    #1;
    tail++;
    $display("BAD timed coroutine tail");
  endtask

  generate
    if (`FINISH_BOUNDARY_CASE == 6) begin : timed_case
      initial begin
        stop_timed();
        tail++;
        $display("BAD timed caller tail");
      end
    end
    else begin : ordinary_case
      initial begin
        #1;
        seed += 3;
        `queue_update;
        if (`FINISH_BOUNDARY_CASE == 2 || `FINISH_BOUNDARY_CASE == 8) begin
          $strobe("GOOD postponed case=%0d q=%0d word7=%0d", `FINISH_BOUNDARY_CASE, q, word7);
          #1;
          `checkd(q, 1);
          `checkh(word7, 7'd20);
          `checkh(word65, 65'd20 << 33);
          entered++;
          if (`FINISH_BOUNDARY_CASE == 2) begin
            `before_finish;
            $finish(0);
            tail++;
            $display("BAD next-slot tail");
          end
          else begin
            // The control ends naturally, with no finish request anywhere in
            // this elaborated branch, after NBA and postponed work completed.
            function_result = normal_value(seed) + normal_noinline_value(seed);
            `checkd(function_result, 62);
            `checkd(tail, 1);
            ref_owner(function_result, 0, seed);
            tail++;
            `checkd(function_result, 17);
            `checkd(tail, 2);
            // Check the positive side effects before restoring the common
            // final-state baseline used by all termination cases.
            function_result = 41;
            tail = 0;
            $display("CONTROL case=8 time=%0d q=%0d", $time, q);
          end
        end
        else begin
          $strobe("BAD postponed case=%0d q=%0d", `FINISH_BOUNDARY_CASE, q);
          `checkd(q, 0);
          `checkh(word7, '0);
          `checkh(word65, '0);
          if (`FINISH_BOUNDARY_CASE == 0) begin
            entered++;
            `before_finish;
            $finish(0);
            tail++;
            $display("BAD direct tail");
          end
          else if (`FINISH_BOUNDARY_CASE == 1) begin
            #0;
            `checkd(q, 0);
            entered++;
            `before_finish;
            $finish(0);
            tail++;
            $display("BAD inactive caller tail");
          end
          else if (`FINISH_BOUNDARY_CASE == 3) begin
            stop_outer();
            tail++;
            $display("BAD task caller tail");
          end
          else if (`FINISH_BOUNDARY_CASE == 4) begin
            `checkd(seed, 20);
            entered++;
            `before_finish;
            ref_owner(function_result, seed == 20, seed);
            tail++;
            $display("BAD function caller tail");
          end
          else if (`FINISH_BOUNDARY_CASE == 9) begin
            `checkd(seed, 20);
            entered++;
            `before_finish;
            function_result = stop_noinline_function(seed, seed == 20);
            tail++;
            $display("BAD noninline function caller tail");
          end
          else if (`FINISH_BOUNDARY_CASE == 5) begin
            for (int index = 0; index < 4; index++) begin
              entered++;
              if (index == seed - 19) begin
                `before_finish;
                $finish(0);
                tail++;
                $display("BAD loop tail");
              end
            end
            tail++;
            $display("BAD loop caller tail");
          end
          else if (`FINISH_BOUNDARY_CASE == 7) begin
            armed = 1;
            wait (inactive_entered != 0);
            `checkd(inactive_entered, 1);
            entered++;
            `before_finish;
            $finish(0);
            tail++;
            $display("BAD inactive parent tail");
          end
        end
      end
    end
    if (`FINISH_BOUNDARY_CASE == 7) begin : inactive_case
      initial begin
        wait (armed);
        inactive_entered = 1;
        // The parent's active wait cannot complete before this child enters;
        // this continuation then waits in inactive, avoiding an ordering race
        // between two continuations in the same inactive queue.
        #0;
        inactive_done++;
        $display("BAD inactive queue tail");
      end
    end
  endgenerate

  final begin
    final_calls++;
    `checkd(final_calls, 1);
    `checkd(seed, 20);
    `checkd(entered, `FINISH_BOUNDARY_CASE == 5 ? 2 : 1);
    `checkd(tail, 0);
    `checkd(inactive_entered, `FINISH_BOUNDARY_CASE == 7 ? 1 : 0);
    `checkd(inactive_done, 0);
    `checkd(function_result, 41);
    `checkd($time, (`FINISH_BOUNDARY_CASE == 2 || `FINISH_BOUNDARY_CASE == 8) ? 2 : 1);
    `checkd(q, (`FINISH_BOUNDARY_CASE == 2 || `FINISH_BOUNDARY_CASE == 8) ? 1 : 0);
    `checkh(word7, (`FINISH_BOUNDARY_CASE == 2 || `FINISH_BOUNDARY_CASE == 8) ? 7'd20 : '0);
    `checkh(word65,
            (`FINISH_BOUNDARY_CASE == 2 || `FINISH_BOUNDARY_CASE == 8) ? (65'd20 << 33) : '0);
    $display(
        "FINAL case=%0d time=%0d q=%0d checks=%0d final=%0d entered=%0d inactive=%0d result=%0d",
        `FINISH_BOUNDARY_CASE, $time, q, checks, final_calls, entered, inactive_done,
        function_result);
    $display("*-* All Finished *-*");
  end
endmodule
