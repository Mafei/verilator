// DESCRIPTION: Verilator: Clocking outputs and forward-only input connections
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d:  got=%p exp=%p (%s !== %s)\n", `__FILE__,`__LINE__, (gotv), (expv), `"gotv`", `"expv`"); `stop; end while(0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

typedef struct packed {
  logic [6:0] hi;
  logic [7:0] lo;
} packet_t;

// Distinct interface types keep each class driver tied to its own interface.
interface flat_sender_if (input wire clk, output wire [14:0] bus);
  timeunit 1ns;
  timeprecision 1ps;
  clocking cb @(posedge clk);
    default input #1step output #1step;
    output bus;
  endclocking
  class driver_t;
    task drive(input logic [14:0] value);
      cb.bus <= value;
      @(cb);
    endtask
  endclass
  driver_t driver = new;
endinterface

interface concat_sender_if (input wire clk, output wire [14:0] bus);
  timeunit 1ns;
  timeprecision 1ps;
  clocking cb @(posedge clk);
    default input #1step output #1step;
    output bus;
  endclocking
  class driver_t;
    task drive(input logic [14:0] value);
      cb.bus <= value;
      @(cb);
    endtask
  endclass
  driver_t driver = new;
endinterface

interface task_sender_if (input wire clk, output wire [14:0] bus);
  timeunit 1ns;
  timeprecision 1ps;
  clocking cb @(posedge clk);
    default input #1step output #1step;
    output bus;
  endclocking
  task automatic drive(input logic [14:0] value);
    cb.bus <= value;
    @(cb);
  endtask
endinterface

interface passive_if (input wire clk, input wire [14:0] bus);
  timeunit 1ns;
  timeprecision 1ps;
  clocking sampled_cb @(posedge clk);
    input #1step bus;
  endclocking
  // Merely declaring an output clockvar must not reverse this input port.
  // No process drives this clockvar or writes the input net.
  /* verilator lint_off ASSIGNIN */
  clocking unused_cb @(posedge clk);
    output #1step bus;
  endclocking
  /* verilator lint_on ASSIGNIN */
endinterface

module t;
  timeunit 1ns;
  timeprecision 1ps;
  bit clk = 0;
  always #5ns clk = ~clk;

  wire [14:0] flat_bus;
  wire [9:3] concat_hi;
  wire [10:3] concat_lo;
  wire [14:0] task_bus;
  wire [6:0] direct_hi;
  wire [7:0] direct_lo;
  flat_sender_if flat_sender (clk, flat_bus);
  concat_sender_if concat_sender (clk, {concat_hi, concat_lo});
  task_sender_if task_sender (clk, task_bus);
  task_sender_if direct_sender (clk, {direct_hi, direct_lo});

  logic [14:0] a = 0;
  logic [14:0] b = 0;
  logic [6:0] pattern_hi = 0;
  logic [7:0] pattern_lo = 0;
  logic [6:0] passive_hi = 0;
  logic [7:0] passive_lo = 0;
  passive_if arithmetic (clk, a + b);
  passive_if pattern_value (clk, packet_t'{hi: pattern_hi, lo: pattern_lo});
  passive_if independent_concat (clk, {passive_hi, passive_lo});

  initial begin
    logic [14:0] value;
    logic [14:0] previous;
    logic [14:0] expected_a;
    logic [14:0] expected_b;
    packet_t expected_pattern;
    logic [14:0] expected_concat;
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    previous = 0;
    for (int i = 0; i < 8; ++i) begin
      @(negedge clk);
      value = 15'(i * 5281 + 5779);
      expected_a = 15'(i * 317 + 53);
      expected_b = 15'(i * 521 + 109);
      expected_pattern = packet_t'(15'(i * 911 + 73));
      expected_concat = 15'(i * 701 + 211);
      a = expected_a;
      b = expected_b;
      pattern_hi = expected_pattern.hi;
      pattern_lo = expected_pattern.lo;
      {passive_hi, passive_lo} = expected_concat;
      #1ns;
      fork
        flat_sender.driver.drive(value);
        concat_sender.driver.drive(value ^ 15'h56d3);
        task_sender.drive(~value);
        begin
          direct_sender.cb.bus <= 15'(value + 15'h72d);
          @(direct_sender.cb);
        end
      join
      // The #1step output skew has not elapsed at the clocking event.
      if (i != 0) begin
        `checkh(flat_bus, previous);
        `checkh({concat_hi, concat_lo}, previous ^ 15'h56d3);
        `checkh(task_bus, 15'(~previous));
        `checkh({direct_hi, direct_lo}, 15'(previous + 15'h72d));
      end
      `checkh(arithmetic.sampled_cb.bus, 15'(expected_a + expected_b));
      `checkh(pattern_value.sampled_cb.bus, expected_pattern);
      `checkh(independent_concat.sampled_cb.bus, expected_concat);
      #2ps;
      `checkh(flat_bus, value);
      `checkh({concat_hi, concat_lo}, value ^ 15'h56d3);
      `checkh(task_bus, 15'(~value));
      `checkh({direct_hi, direct_lo}, 15'(value + 15'h72d));
      `checkh(arithmetic.bus, 15'(expected_a + expected_b));
      `checkh(pattern_value.bus, expected_pattern);
      `checkh(independent_concat.bus, expected_concat);
      `checkh(a, expected_a);
      `checkh(b, expected_b);
      `checkh({pattern_hi, pattern_lo}, expected_pattern);
      `checkh({passive_hi, passive_lo}, expected_concat);
      $display("settled cycle=%0d value=%h flat=%h concat=%h task=%h direct=%h", i,
               value, flat_bus, {concat_hi, concat_lo}, task_bus, {direct_hi, direct_lo});
      #1ns;
      `checkh(flat_bus, value);
      `checkh({concat_hi, concat_lo}, value ^ 15'h56d3);
      `checkh(task_bus, 15'(~value));
      `checkh({direct_hi, direct_lo}, 15'(value + 15'h72d));
      `checkh(arithmetic.bus, 15'(expected_a + expected_b));
      `checkh(pattern_value.bus, expected_pattern);
      `checkh(independent_concat.bus, expected_concat);
      `checkh(a, expected_a);
      `checkh(b, expected_b);
      `checkh({pattern_hi, pattern_lo}, expected_pattern);
      `checkh({passive_hi, passive_lo}, expected_concat);
      previous = value;
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
