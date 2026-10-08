// DESCRIPTION: Verilator: Preserve signed indices through full-domain bounds checks
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
  wire [4:0] done;
  wire min_done;
  bit narrow_done = 0;
  logic [6:0] narrow_packed = '1;
  logic [7:0] narrow_array[0:6];
  wire [7:0] narrow_array_probe = narrow_array[3];
  bit signed [2:0] narrow_index = 0;
  bit narrow_read = 0;
  typedef bit [7:0] two_byte;
  two_byte narrow_array_read = 0;
  signed_domain_width #(7) w7 (done[0]);
  signed_domain_width #(17) w17 (done[1]);
  signed_domain_width #(33) w33 (done[2]);
  signed_domain_width #(65) w65 (done[3]);
  signed_domain_width #(129) w129 (done[4]);
  signed_domain_min min_bound (min_done);
  wire [31:0] total_checks = checks + w7.checks + w17.checks + w33.checks
      + w65.checks + w129.checks + min_bound.checks;

  initial begin
    for (int i = 0; i < 7; i++) narrow_array[i] = 8'h55;
    #1;
    narrow_index = -1;
    narrow_read = bit'(narrow_packed[narrow_index]);
    narrow_array_read = two_byte'(narrow_array[narrow_index]);
    `checkh(narrow_read, 1'b0)
    `checkh(narrow_array_read, 8'h00)
    narrow_packed[narrow_index] = 0;
    narrow_array[narrow_index] = 0;
    `checkh(narrow_packed, 7'h7f)
    for (int i = 0; i < 7; i++) `checkh(narrow_array[i], 8'h55)
    #1;
    narrow_index = -2;
    narrow_read = bit'(narrow_packed[narrow_index]);
    narrow_array_read = two_byte'(narrow_array[narrow_index]);
    `checkh(narrow_read, 1'b0)
    `checkh(narrow_array_read, 8'h00)
    narrow_packed[narrow_index] = 0;
    narrow_array[narrow_index] = 0;
    `checkh(narrow_packed, 7'h7f)
    for (int i = 0; i < 7; i++) `checkh(narrow_array[i], 8'h55)
    #1;
    narrow_index = 3;
    narrow_packed[narrow_index] = 0;
    narrow_array[narrow_index] = 0;
    `checkh(narrow_packed, 7'h77)
    `checkh(narrow_array[3], 8'h00)
    narrow_done = 1;
  end

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #20;
    `checkh(done, 5'b11111)
    `checkh(min_done, 1'b1)
    `checkh(narrow_done, 1'b1)
    $display(
        "Signed domain checks: %0d",
        checks + w7.checks + w17.checks + w33.checks + w65.checks + w129.checks + min_bound.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module signed_domain_width #(
    parameter int WIDTH = 7
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  logic [WIDTH-1:0] down = '0;
  logic [0:WIDTH-1] up = '0;
  logic [WIDTH+5:6] nonzero = '0;
  logic [-2:WIDTH-3] negative = '0;
  logic [7:0] memory[-2:WIDTH-3];
  wire [7:0] memory_probe = memory[WIDTH-3];
  bit sampled = 0;
  typedef bit [7:0] two_byte;
  two_byte sampled_array = 0;
  bit valid_read65 = 0, valid_read95 = 0;
  bit signed [64:0] index65 = 0;
  bit signed [94:0] index95 = 0;
  bit [31:0] calls = 0;

  function automatic int counted(input int value);
    calls++;
    return value;
  endfunction

  task automatic check_values;
    // The expected values are literals, independent of the indexed writer.
    `checkh(down, '1)
    `checkh(up, '1)
    `checkh(nonzero, '1)
    `checkh(negative, '1)
    for (int i = 0; i < WIDTH; i++) `checkh(memory[i-2], 8'h55)
  endtask

  task automatic invalid_index(input bit signed [94:0] invalid);
    // Explicit two-state conversion maps an invalid four-state read to zero.
    // The driver also fixes --x-assign 0, without claiming X/Z simulation.
    index95 = invalid;
    sampled = bit'(down[invalid]);
    `checkh(sampled, 1'b0)
    sampled = bit'(up[invalid]);
    `checkh(sampled, 1'b0)
    sampled = bit'(nonzero[invalid+6]);
    `checkh(sampled, 1'b0)
    sampled = bit'(negative[invalid-2]);
    `checkh(sampled, 1'b0)
    sampled_array = two_byte'(memory[invalid-2]);
    `checkh(sampled_array, 8'h00)
    down[invalid] = 0;
    up[invalid] = 0;
    nonzero[invalid+6] = 0;
    negative[invalid-2] = 0;
    memory[invalid-2] = 0;
    check_values();
  endtask

  initial begin
    for (int i = 0; i < WIDTH; i++) begin
      down[i] = 1;
      up[i] = 1;
      nonzero[i+6] = 1;
      negative[i-2] = 1;
      memory[i-2] = 8'h55;
    end
    check_values();
    #1;
    invalid_index(-1);
    #1;
    invalid_index(-2);
    #1;
    invalid_index(WIDTH);
    #1;
    invalid_index(WIDTH + 1);
    #1;
    invalid_index(256);
    #1;
    invalid_index(-256);
    // Icarus 12 truncates these two indices to low32 and fails the full oracle.
    // This optional reference-only subset keeps the physical schedule unchanged.
    // The Verilator regression always runs the full mathematical domain.
`ifdef SIGNED_INDEX_REFERENCE_COMMON
    #2;
`else
    #1;
    invalid_index(95'sh10000000000);
    #1;
    invalid_index(-95'sh10000000000);
`endif
    #1;
    index65 = 65'(WIDTH - 1);
    index95 = 95'(WIDTH - 1);
    valid_read65 = down[index65];
    `checkh(valid_read65, 1'b1)
    down[index65] = 0;
    valid_read95 = down[index95];
    `checkh(valid_read95, 1'b0)
    memory[index95-2] = 0;
    sampled_array = two_byte'(memory[index65-2]);
    `checkh(sampled_array, 8'h00)
    #1;
    down[index95] = 1;
    memory[index65-2] = 8'h55;
    check_values();
    #1;
    down[counted(WIDTH-1)] = 0;
    `checkd(calls, 1)
    #1;
    sampled = down[counted(WIDTH-1)];
    `checkh(sampled, 1'b0)
    `checkd(calls, 2)
    #1;
    down[counted(WIDTH-1)] = 1;
    `checkd(calls, 3)
    #1;
    down[counted(256)] = 0;
    `checkd(calls, 4)
    #1;
    sampled = down[counted(256)];
    `checkh(sampled, 1'b0)
    `checkd(calls, 5)
    check_values();
    #1;
    done = 1;
  end
endmodule

module signed_domain_min (
    output bit done = 0
);
  localparam int MIN_BOUND = -2147483648;
  bit [31:0] checks = 0;
  logic [MIN_BOUND+1:MIN_BOUND] down = 2'b10;
  logic [MIN_BOUND:MIN_BOUND+1] up = 2'b10;
  bit signed [94:0] index = 0;
  bit sampled = 0;

  task automatic check(input bit expected_down, input bit expected_up);
    sampled = bit'(down[index]);
    `checkh(sampled, expected_down)
    sampled = bit'(up[index]);
    `checkh(sampled, expected_up)
  endtask

  initial begin
    #1;
    index = 95'(MIN_BOUND);
    check(0, 1);
    #1;
    index = 95'(MIN_BOUND + 1);
    check(1, 0);
    #1;
    index = 95'(MIN_BOUND) - 1;
    check(0, 0);
    #1;
    index = 95'(MIN_BOUND) + 2;
    check(0, 0);
    `checkh({down, up}, 4'b1010)
    done = 1;
  end
endmodule
