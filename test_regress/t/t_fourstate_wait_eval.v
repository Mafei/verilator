// DESCRIPTION: Verilator: Reevaluate four-state wait conditions at wakeup
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%p expected=%p\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

module t;
  bit [3:0] drive = 0;
  wire [3:0] ready = drive;
  logic [64:0] wide = 0;
  logic [64:0] immediate;
  bit bit_ready = 0;
  bit [7:0] done = 0;
  bit [31:0] checks = 0;
  bit [31:0] calls = 0;
  logic [1:0][6:0] lanes = 0;
  bit [1:0] lane_done = 0;

  function automatic logic [64:0] sample(input logic [64:0] value);
    calls++;
    return value;
  endfunction

  initial begin
`ifdef FOURSTATE_EXPECT
    immediate = 'x;
`else
    immediate = '0;
`endif
    immediate[64] = 1;
    #1;
    drive = 4'hf;
`ifdef FOURSTATE_EXPECT
    wide = 'x;
`endif
    #1;
`ifdef FOURSTATE_EXPECT
    wide = 'z;
`endif
    bit_ready = 1;
    lanes[0] = '1;
    #1;
    wide[64] = 1;
    #1;
    wide = '1;
    lanes[1] = '1;
  end

  initial begin
    wait (&ready);
    `checkh($time, 64'd1);
    `checkh(ready, 4'hf);
    done[0] = 1;
  end

  initial begin
    wait (ready === 4'hf);
    `checkh($time, 64'd1);
    `checkh(ready, 4'hf);
    done[1] = 1;
  end

  initial begin
    // Deliberately test the implicit truth conversion of an entire vector.
    // verilator lint_off WIDTHTRUNC
    wait (wide);
    // verilator lint_on WIDTHTRUNC
    `checkh($time, 64'd3);
    `checkh(wide[64], 1'b1);
    done[2] = 1;
  end

  initial begin
    wait (&wide);
    `checkh($time, 64'd4);
    `checkh(wide, 65'h1_ffff_ffff_ffff_ffff);
    done[3] = 1;
  end

  initial begin
    wait (wide === '1);
    `checkh($time, 64'd4);
    `checkh(wide, 65'h1_ffff_ffff_ffff_ffff);
    done[4] = 1;
  end

  initial begin
    #1ps;
    // verilator lint_off WIDTHTRUNC
    wait (immediate);
    // verilator lint_on WIDTHTRUNC
    `checkh($time, 64'd0);
    `checkh(immediate[64], 1'b1);
    done[5] = 1;
  end

  initial begin
    #1ps;
    `checkh(calls, 32'd0);
    // verilator lint_off WIDTHTRUNC
    wait (sample(immediate));
    // verilator lint_on WIDTHTRUNC
    `checkh(calls, 32'd1);
    `checkh($time, 64'd0);
    done[6] = 1;
  end

  initial begin
    wait (bit_ready);
    `checkh($time, 64'd2);
    `checkh(bit_ready, 1'b1);
    done[7] = 1;
  end

  task automatic wait_lane(input bit lane, input bit [63:0] expected_time);
    // verilator no_inline_task
    wait (&lanes[lane]);
    `checkh($time, expected_time);
    `checkh(lanes[lane], 7'h7f);
    lane_done[lane] = 1;
  endtask

  initial begin
    fork
      wait_lane(0, 64'd2);
      wait_lane(1, 64'd4);
    join
  end

  initial begin
    wait ((&done) && (&lane_done));
    #1ps;
    if (checks != 21) $fatal(1, "Missing wait condition checks");
    $display("WAIT_EVAL_PASS checks=%0d calls=%0d", checks, calls);
    $write("*-* All Finished *-*\n");
    $finish;
  end

  initial begin
    #6;
    $fatal(1, "WAIT_EVAL_TIMEOUT done=%h checks=%0d", done, checks);
  end
endmodule
