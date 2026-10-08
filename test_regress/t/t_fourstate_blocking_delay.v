// DESCRIPTION: Verilator: Activation-local four-state blocking delay snapshots
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
module t;
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  wire [5:0] done;
  blocking_width #(1) w1 (done[0]);
  blocking_width #(7) w7 (done[1]);
  blocking_width #(17) w17 (done[2]);
  blocking_width #(33) w33 (done[3]);
  blocking_width #(65) w65 (done[4]);
  blocking_width #(129) w129 (done[5]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #60;
    `checkh(done, 6'b111111)
    $display("Blocking delay checks: %0d",
             w1.checks + w7.checks + w17.checks + w33.checks + w65.checks + w129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module blocking_width #(
    parameter int WIDTH = 1
) (
    output wire done
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  bit serial_done = 0, fork_done = 0, armed = 0;
  assign done = serial_done & fork_done;
  reg [WIDTH-1:0] source = '0, result = '0;
  reg [3:0] delay_source = 3;
  bit [31:0] rhs_calls = 0, delay_calls = 0, completions = 0, events = 0;
  time next_time = 0, last_change = 0;
  reg [WIDTH-1:0] fork_source = '0, fork_result = '0, fork_follow = '0;
  reg [3:0] fork_delay = 0;
  bit [31:0] fork_rhs_calls = 0, fork_delay_calls = 0, fork_completions = 0, fork_events = 0;
  time fork_next_time = 0, fork_last_change = 0;

  function automatic logic [WIDTH-1:0] pattern(input int seed);
    for (int i = 0; i < WIDTH; i++) pattern[i] = drive_state((i + seed) % 4);
  endfunction
  function automatic logic [WIDTH-1:0] snapshot(input logic [WIDTH-1:0] value);
    rhs_calls++;
    return value;
  endfunction
  function automatic logic [3:0] delay_once(input logic [3:0] value);
    delay_calls++;
    return value;
  endfunction
  function automatic logic [WIDTH-1:0] fork_snapshot(input logic [WIDTH-1:0] value);
    fork_rhs_calls++;
    return value;
  endfunction
  function automatic logic [3:0] fork_delay_once(input logic [3:0] value);
    fork_delay_calls++;
    return value;
  endfunction

  // The first statement is timed: later getter temporaries need an outer task anchor.
  task automatic drive_fork;
    fork_result = #(fork_delay_once(fork_delay)) fork_snapshot(fork_source);
    fork_follow = fork_delay[0] ? (pattern(0) ^ fork_result) : (pattern(1) ^ fork_result);
    `checkh(fork_follow, pattern(0) ^ fork_result)
    fork_next_time = $time;
    fork_completions++;
    if ($time == 35) begin
      `checkh(fork_result, pattern(3))
    end
    else if ($time == 37) begin
      `checkh(fork_result, pattern(2))
    end
    else if ($time == 45) begin
      `checkh(fork_result, '1)
    end
    else begin
      `checkd($time, 47)
      `checkh(fork_result, 'z)
    end
  endtask

  initial #2 armed = 1;
  always @(result)
    if (armed) begin
      events++;
      last_change = $time;
    end
  always @(fork_result)
    if (armed) begin
      fork_events++;
      fork_last_change = $time;
    end
  initial begin
    #1;
    forever begin
      @(source);
      result = #(delay_once(delay_source)) snapshot(source);
      next_time = $time;
      completions++;
    end
  end
  initial begin
    #10;
    source = pattern(1);
    #1;
    source = pattern(2);  // The process is blocked; this activation is ignored.
    `checkh(result, '0)
    `checkd(completions, 0)
    #3;
    `checkh(result, pattern(1))
    `checkd(rhs_calls, 1)
    `checkd(delay_calls, 1)
    `checkd(completions, 1)
    `checkd(next_time, 13)
    `checkd(events, 1)
    `checkd(last_change, 13)
    source = 'z;
    #4;
    `checkh(result, 'z)
    `checkd(next_time, 17)
    source = '1;
    #4;
    `checkh(result, '1)
    `checkd(next_time, 21)
    source = '1;
    #3;
    `checkd(rhs_calls, 3)
    `checkd(delay_calls, 3)
    `checkd(completions, 3)
    `checkd(events, 3)
    delay_source = 4'b1x00;
    source = pattern(2);
    #1;
    `checkh(result, pattern(2))
    `checkd(next_time, 25)
    delay_source = 4'bzzz1;
    source = pattern(1);
    #1;
    `checkh(result, pattern(1))
    `checkd(next_time, 26)
    delay_source = 0;
    source = '0;
    #1;
    `checkh(result, '0)
    `checkd(next_time, 27)
    source = '0;
    #1;
    `checkd(rhs_calls, 6)
    `checkd(delay_calls, 6)
    `checkd(completions, 6)
    `checkd(events, 6)
    `checkd(last_change, 27)
    serial_done = 1;
  end

  initial begin
    #30;
    for (int round = 0; round < 2; round++) begin
      fork_source = round == 0 ? pattern(2) : 'z;
      fork_delay = 6;
      for (int launch = 0; launch < 2; launch++) begin
        fork
          begin
            #1;
            // Concurrent invocations execute the same assignment with different snapshots.
            drive_fork();
          end
        join_none
        #2;
        if (launch == 0) begin
          fork_source = round == 0 ? pattern(3) : '1;
          fork_delay = 2;
        end
        else begin
          fork_source = '0;
          fork_delay = 1;
        end
      end
      // Both independent children must finish by 37/47, before this fixed checkpoint.
      #4;
      `checkh(fork_result, round == 0 ? pattern(2) : {WIDTH{1'bz}})
      `checkd(fork_rhs_calls, 2 * (round + 1))
      `checkd(fork_delay_calls, 2 * (round + 1))
      `checkd(fork_completions, 2 * (round + 1))
      `checkd(fork_events, 2 * (round + 1))
      `checkd(fork_next_time, 37 + 10 * round)
      `checkd(fork_last_change, 37 + 10 * round)
      #2;
    end
    fork_done = 1;
  end
endmodule
