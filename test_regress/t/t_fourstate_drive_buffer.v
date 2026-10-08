// DESCRIPTION: Verilator: Four-state isolated drive semantics
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
module t;
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  wire [11:0] done;
  buffer_width #(1) w1 (done[0]);
  buffer_width #(7) w7 (done[1]);
  buffer_width #(17) w17 (done[2]);
  buffer_width #(33) w33 (done[3]);
  buffer_width #(65) w65 (done[4]);
  buffer_width #(129) w129 (done[5]);
  buffer_expression #(17) x17 (done[6]);
  buffer_expression #(24) x24 (done[7]);
  buffer_expression #(31) x31 (done[8]);
  buffer_expression #(32) x32 (done[9]);
  buffer_expression #(63) x63 (done[10]);
  buffer_expression #(64) x64 (done[11]);
  wire [63:0] constants;
  wire [3:0] plain_constants;
  for (genvar data = 0; data < 4; data++) begin : p
    buffer_plain_constant #(data) u (plain_constants[data]);
  end
  for (genvar kind = 0; kind < 4; kind++) begin : k
    for (genvar en = 0; en < 4; en++) begin : e
      for (genvar data = 0; data < 4; data++) begin : d
        buffer_constant #(kind, en, data) u (constants[kind*16+en*4+data]);
      end
    end
  end
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #5;
    for (int kind = 0; kind < 4; kind++) begin
      for (int en = 0; en < 4; en++) begin
        for (int data = 0; data < 4; data++) begin
          `checkh(constants[kind*16+en*4+data], drive_literal(kind, en * 4 + data))
        end
      end
    end
    // IV12 folds the literal-Z buf to Z; retain the IEEE 1800-2017 Table 28-4
    // expectation here. This macro is only for a separate dynamic reference probe.
`ifndef GATE_BUF_DYNAMIC_ONLY
    for (int data = 0; data < 4; data++) begin
      `checkh(plain_constants[data], drive_literal(0, 4 + data))
    end
`endif
    #200;
    `checkh(done, 12'hfff)
    $display("Buffer dynamic checks: %0d",
             w1.checks + w7.checks + w17.checks + w33.checks + w65.checks + w129.checks);
    $display("Buffer constant checks: %0d", checks - 1);
    $display("Buffer expression checks: %0d",
             x17.checks + x24.checks + x31.checks + x32.checks + x63.checks + x64.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module buffer_width #(
    parameter int WIDTH = 1
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  reg [WIDTH-1:0] source_enable = '0, source_data = '0;
  wire [0:WIDTH-1] ascending_data = source_data;
  wire [WIDTH+4:5] ranged_enable = source_enable;
  wire [WIDTH-1:0] buffer1, inverter1;
  wire [WIDTH-1:0] plain_buffer0, plain_buffer1;
  wire [0:WIDTH-1] ascending_buffer0;
  wire [WIDTH+4:5] ranged_inverter0;
  wire [WIDTH-1:0] buffer0 = ascending_buffer0, inverter0 = ranged_inverter0;
  bufif1 b1[WIDTH-1:0] (buffer1, ascending_data, ranged_enable);
  bufif0 b0[WIDTH-1:0] (ascending_buffer0, ascending_data, ranged_enable);
  notif1 n1[WIDTH-1:0] (inverter1, ascending_data, ranged_enable);
  notif0 n0[WIDTH-1:0] (ranged_inverter0, ascending_data, ranged_enable);
  // Unlike a continuous wire assignment, logic buf maps both X and Z inputs to X.
  buf plain[WIDTH-1:0] (plain_buffer0, plain_buffer1, ascending_data);
  initial begin
    #10;
    for (int phase = 0; phase < 16; phase++) begin
      for (int bitno = 0; bitno < WIDTH; bitno++) begin
        source_enable[bitno] = drive_state((phase % 4 + bitno) % 4);
        source_data[bitno] = drive_state((phase / 4 + bitno) % 4);
      end
      #10;
      for (int bitno = 0; bitno < WIDTH; bitno++) begin
        `checkh(buffer1[bitno], drive_literal(
                0, ((phase % 4 + bitno) % 4) * 4 + (phase / 4 + bitno) % 4))
        `checkh(buffer0[bitno], drive_literal(
                1, ((phase % 4 + bitno) % 4) * 4 + (phase / 4 + bitno) % 4))
        `checkh(inverter1[bitno], drive_literal(
                2, ((phase % 4 + bitno) % 4) * 4 + (phase / 4 + bitno) % 4))
        `checkh(inverter0[bitno], drive_literal(
                3, ((phase % 4 + bitno) % 4) * 4 + (phase / 4 + bitno) % 4))
        `checkh(plain_buffer0[bitno], drive_literal(0, 4 + (phase / 4 + bitno) % 4))
        `checkh(plain_buffer1[bitno], drive_literal(0, 4 + (phase / 4 + bitno) % 4))
      end
      #1;
    end
    done = 1;
  end
endmodule

module buffer_constant #(
    parameter int KIND = 0,
    ENABLE = 0,
    DATA = 0
) (
    output wire result
);
  localparam logic E = ENABLE == 0 ? 1'b0 : ENABLE == 1 ? 1'b1 : ENABLE == 2 ? 1'bx : 1'bz;
  localparam logic D = DATA == 0 ? 1'b0 : DATA == 1 ? 1'b1 : DATA == 2 ? 1'bx : 1'bz;
  if (KIND == 0) bufif1 b (result, D, E);
  else if (KIND == 1) bufif0 b (result, D, E);
  else if (KIND == 2) notif1 n (result, D, E);
  else notif0 n (result, D, E);
endmodule

module buffer_plain_constant #(
    parameter int DATA = 0
) (
    output wire result
);
  localparam logic D = DATA == 0 ? 1'b0 : DATA == 1 ? 1'b1 : DATA == 2 ? 1'bx : 1'bz;
  buf b (result, D);
endmodule

module buffer_expression #(
    parameter int WIDTH = 17
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  reg [WIDTH-1:0] enable_a = '0, data_a = '0;
  reg [WIDTH-1:0] enable_b = '0, data_b = '0, data_c = '0;
  reg branch = 0;
  bit [WIDTH-1:0] known_enable = '0;
  wire [WIDTH-1:0] result_a, result_b, result_known, result_plain;
  function automatic logic [WIDTH-1:0] rotate(input logic [WIDTH-1:0] value);
    // verilator no_inline_task
    return {value[WIDTH-2:0], value[WIDTH-1]};
  endfunction
  function automatic bit [WIDTH-1:0] rotate_known(input bit [WIDTH-1:0] value);
    // verilator no_inline_task
    return {value[WIDTH-2:0], value[WIDTH-1]};
  endfunction
  bufif1 a[WIDTH-1:0] (result_a, rotate (data_a), rotate (enable_a));
  notif0 b[WIDTH-1:0] (result_b, branch ? data_b : data_c, enable_b);
  bufif1 known[WIDTH-1:0] (result_known, rotate (data_c), rotate_known (known_enable));
  buf plain[WIDTH-1:0] (result_plain, rotate (data_c));
  initial begin
    #10;
    for (int phase = 0; phase < 32; phase++) begin
      for (int bitno = 0; bitno < WIDTH; bitno++) begin
        enable_a[bitno] = drive_state((phase % 4 + bitno) % 4);
        data_a[bitno] = drive_state((phase / 4 + bitno) % 4);
        if (phase % 2 == 0) begin
          enable_b[bitno] = drive_state((phase % 4 + bitno + 1) % 4);
          data_b[bitno] = drive_state((phase / 4 + bitno + 1) % 4);
          data_c[bitno] = drive_state((phase / 8 + 3 * bitno + 1) % 4);
          known_enable[bitno] = ((phase / 2 + bitno) % 2) != 0;
        end
      end
      if (phase % 2 == 0) branch = drive_state((phase / 4) % 4);
      #2;
      for (int bitno = 0; bitno < WIDTH; bitno++) begin
        `checkh(result_a[bitno], drive_literal(
                0,
                4 * drive_code(
                    enable_a[(bitno+WIDTH-1)%WIDTH]
                ) + drive_code(
                    data_a[(bitno+WIDTH-1)%WIDTH])
                ))
        `checkh(result_b[bitno], drive_literal(
                3,
                4 * drive_code(
                    enable_b[bitno]
                ) + drive_code(
                    drive_merge(branch, data_b[bitno], data_c[bitno]))
                ))
        `checkh(result_known[bitno], drive_literal(
                0,
                4 * int'(known_enable[(bitno+WIDTH-1)%WIDTH]) + drive_code(
                    data_c[(bitno+WIDTH-1)%WIDTH])
                ))
        `checkh(result_plain[bitno], drive_literal(0, 4 + drive_code(data_c[(bitno+WIDTH-1)%WIDTH])
                ))
      end
      #1;
    end
    done = 1;
  end
endmodule
