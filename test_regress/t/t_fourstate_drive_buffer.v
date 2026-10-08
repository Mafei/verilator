// DESCRIPTION: Verilator: Four-state isolated drive semantics
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
module t;
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  wire [5:0] done;
  buffer_width #(1) w1 (done[0]);
  buffer_width #(7) w7 (done[1]);
  buffer_width #(17) w17 (done[2]);
  buffer_width #(33) w33 (done[3]);
  buffer_width #(65) w65 (done[4]);
  buffer_width #(129) w129 (done[5]);
  wire [63:0] constants;
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
    #200;
    `checkh(done, 6'b111111)
    $display("Buffer dynamic checks: %0d",
             w1.checks + w7.checks + w17.checks + w33.checks + w65.checks + w129.checks);
    $display("Buffer constant checks: %0d", checks - 1);
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
  wire [0:WIDTH-1] ascending_buffer0;
  wire [WIDTH+4:5] ranged_inverter0;
  wire [WIDTH-1:0] buffer0 = ascending_buffer0, inverter0 = ranged_inverter0;
  bufif1 b1[WIDTH-1:0] (buffer1, ascending_data, ranged_enable);
  bufif0 b0[WIDTH-1:0] (ascending_buffer0, ascending_data, ranged_enable);
  notif1 n1[WIDTH-1:0] (inverter1, ascending_data, ranged_enable);
  notif0 n0[WIDTH-1:0] (ranged_inverter0, ascending_data, ranged_enable);
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
