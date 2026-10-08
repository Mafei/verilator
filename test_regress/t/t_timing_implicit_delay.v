// DESCRIPTION: Verilator: Timed implicit event controls rearm after completion
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  bit [31:0] checks = 0;
  wire [5:0] done;
  bit never_hit = 0;
  bit indexed_done = 0;
  reg [6:0] indexed_source = 7'b1000001;
  bit [2:0] index = 0;
  reg indexed_result = 0;
  bit [31:0] indexed_completions = 0;
  time indexed_at = 0;
  bit nested_done = 0;
  reg nested_source = 0, nested_result = 0;
  bit nested_event = 0;
  bit [31:0] nested_completions = 0;
  time nested_at = 0;
  implicit_width #(1) w1 (done[0]);
  implicit_width #(7) w7 (done[1]);
  implicit_width #(17) w17 (done[2]);
  implicit_width #(33) w33 (done[3]);
  implicit_width #(65) w65 (done[4]);
  implicit_width #(129) w129 (done[5]);

  // A delay alone does not supply an input to the implicit event expression.
  always @* begin
    #2;
    never_hit = 1;
  end

  always @* begin
    indexed_result = #3 indexed_source[index];
    indexed_completions++;
    indexed_at = $time;
  end

  // A read used only by a nested event expression is excluded from the enclosing @*.
  always @* begin
    nested_result = #2 nested_source;
    @(nested_event);
    nested_completions++;
    nested_at = $time;
  end

  initial begin
    #1;
    nested_event = 1;
    #8;
    `checkh(nested_result, 1'b0)
    `checkd(nested_completions, 0)
    `checkd(nested_at, 0)
    #1;
    nested_source = 1;
    #3;
    nested_event = 0;
    #2;
    nested_event = 1;
    #1;
    `checkh(nested_result, 1'b1)
    `checkd(nested_completions, 1)
    `checkd(nested_at, 13)
    #1;
    nested_source = 0;
    #3;
    nested_event = 0;
    #1;
    `checkh(nested_result, 1'b0)
    `checkd(nested_completions, 2)
    `checkd(nested_at, 20)
    #1;
    `checkh(nested_result, 1'b0)
    `checkd(nested_completions, 2)
    `checkd(nested_at, 20)
    nested_done = 1;
  end

  initial begin
    #10;
    index = 6;
    #1;
    index = 1;
    #3;
    `checkh(indexed_result, 1'b1)
    `checkd(indexed_completions, 1)
    `checkd(indexed_at, 13)
    #1;
    index = 2;
    #4;
    `checkh(indexed_result, 1'b0)
    `checkd(indexed_completions, 2)
    `checkd(indexed_at, 18)
    indexed_source[2] = 1;
    #1;
    indexed_source[0] = 0;
    #3;
    `checkh(indexed_result, 1'b1)
    `checkd(indexed_completions, 3)
    `checkd(indexed_at, 22)
    #1;
    // A dynamic select includes its index and the entire source vector in @*.
`ifdef IMPLICIT_FOURSTATE
    indexed_source[6] = 1'bx;
`else
    indexed_source[6] = 0;
`endif
    #1;
`ifdef IMPLICIT_FOURSTATE
    indexed_source[6] = 1'bz;
`endif
    #3;
    `checkh(indexed_result, 1'b1)
    `checkd(indexed_completions, 4)
    `checkd(indexed_at, 27)
    #1;
`ifdef IMPLICIT_FOURSTATE
    indexed_source[6] = 0;
`else
    indexed_source[6] = 1;
`endif
    #4;
    `checkh(indexed_result, 1'b1)
    `checkd(indexed_completions, 5)
    `checkd(indexed_at, 32)
    indexed_done = 1;
  end

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #55;
    `checkh(done, '1)
    `checkh(never_hit, 1'b0)
    `checkh(indexed_done, 1'b1)
    `checkh(nested_done, 1'b1)
    $display("Implicit delay checks: %0d",
             checks + w1.checks + w7.checks + w17.checks + w33.checks + w65.checks + w129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module implicit_width #(
    parameter int WIDTH = 1
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  reg [WIDTH-1:0] source = '0, result = '0, explicit_result = '0;
  reg [WIDTH-1:0] hidden = '0, function_result = '0;
  reg [WIDTH-1:0] delay_source = '0, delay_result = '0;
  bit [3:0] delay_ticks = 3;
  bit [31:0] completions = 0, explicit_completions = 0;
  bit [31:0] function_completions = 0, delay_completions = 0;
  time completed_at = 0, explicit_at = 0, function_at = 0, delay_at = 0;

  function automatic logic [WIDTH-1:0] pattern(input int seed);
    for (int i = 0; i < WIDTH; i++) begin
`ifdef IMPLICIT_FOURSTATE
      case ((i + seed) % 4)
        0: pattern[i] = 1'b0;
        1: pattern[i] = 1'b1;
        2: pattern[i] = 1'bx;
        3: pattern[i] = 1'bz;
      endcase
`else
      pattern[i] = 1'((i + seed) % 2);
`endif
    end
  endfunction

  // @* includes the call argument, but not this function's hidden global read.
  function automatic logic [WIDTH-1:0] translated(input logic [WIDTH-1:0] value);
    return value ^ hidden;
  endfunction

  function automatic logic [WIDTH-1:0] function_pattern(input int seed);
    for (int i = 0; i < WIDTH; i++) begin
`ifdef IMPLICIT_FOURSTATE
      case ((i + seed) % 4)
        0: function_pattern[i] = 1'b0;
        1: function_pattern[i] = 1'b1;
        default: function_pattern[i] = 1'bx;
      endcase
`else
      function_pattern[i] = 1'((i + seed) % 2);
`endif
    end
  endfunction

  always @* begin
    result = #3 source;
    completions++;
    completed_at = $time;
  end
  always @(source) begin
    explicit_result = #3 source;
    explicit_completions++;
    explicit_at = $time;
  end
  always @* begin
    function_result = #3 translated(source);
    function_completions++;
    function_at = $time;
  end
  always @* begin
    // The conditional reads delay_ticks independently of its use as a delay expression.
    if (delay_ticks != 0) delay_result = #(delay_ticks) delay_source;
    delay_completions++;
    delay_at = $time;
  end

  initial begin
    // Declaration initialization precedes event waits; later samples avoid delay deadlines.
    #10;
    source = pattern(1);
    #1;
    source = '0;
    #3;
    `checkh(result, pattern(1))
    `checkh(explicit_result, pattern(1))
    `checkh(function_result, function_pattern(1))
    `checkd(completions, 1)
    `checkd(explicit_completions, 1)
    `checkd(function_completions, 1)
    `checkd(completed_at, 13)
    `checkd(explicit_at, 13)
    `checkd(function_at, 13)
    #1;
    hidden = '1;
    #4;
    `checkh(function_result, function_pattern(1))
    `checkd(function_completions, 1)
    `checkd(function_at, 13)
    `checkh(result, pattern(1))
    `checkd(completions, 1)
    #1;
`ifdef IMPLICIT_FOURSTATE
    source = 'z;
`else
    source = '1;
`endif
    #1;
    source = '0;
    #3;
`ifdef IMPLICIT_FOURSTATE
    `checkh(result, 'z)
    `checkh(explicit_result, 'z)
    `checkh(function_result, 'x)
`else
    `checkh(result, '1)
    `checkh(explicit_result, '1)
    `checkh(function_result, '0)
`endif
    `checkd(completions, 2)
    `checkd(explicit_completions, 2)
    `checkd(function_completions, 2)
    `checkd(completed_at, 23)
    `checkd(explicit_at, 23)
    `checkd(function_at, 23)
    #2;
    source = '0;
    #1;
    `checkd(completions, 2)
    `checkd(function_completions, 2)
    #1;
    source = '1;
    #4;
    `checkh(result, '1)
    `checkh(explicit_result, '1)
    `checkh(function_result, '0)
    `checkd(completions, 3)
    `checkd(explicit_completions, 3)
    `checkd(function_completions, 3)
    `checkd(completed_at, 31)
    `checkd(explicit_at, 31)
    `checkd(function_at, 31)
    #3;
    delay_source = pattern(1);
    #1;
    delay_source = pattern(2);
    #3;
    `checkh(delay_result, pattern(1))
    `checkd(delay_completions, 1)
    `checkd(delay_at, 38)
    #1;
    delay_ticks = 1;
    #2;
    `checkh(delay_result, pattern(2))
    `checkd(delay_completions, 2)
    `checkd(delay_at, 41)
    #1;
    delay_ticks = 2;
    #3;
    `checkh(delay_result, pattern(2))
    `checkd(delay_completions, 3)
    `checkd(delay_at, 45)
    #1;
    delay_ticks = 2;
    #2;
    `checkd(delay_completions, 3)
    `checkd(delay_at, 45)
    done = 1;
  end
endmodule
