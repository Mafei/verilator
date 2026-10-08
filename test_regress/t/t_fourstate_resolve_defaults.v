// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

module t;
  `include "t_fourstate_resolve_common.vh"
  wire [5:0] done;
  default_width #(1) w1(done[0]);
  default_width #(7) w7(done[1]);
  default_width #(33) w33(done[2]);
  default_width #(65) w65(done[3]);
  default_width #(95) w95(done[4]);
  default_width #(129) w129(done[5]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #4;
    if (done !== '1) $fatal(1, "Default input checks did not finish");
    $display("Resolver default checks: %0d", w1.checks + w7.checks + w33.checks + w65.checks + w95.checks + w129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module default_width #(parameter int WIDTH = 1)(output bit done = 0);
  typedef logic [WIDTH-1:0] word_t;
  bit [31:0] checks = 0;
  bit armed = 0;
  word_t source = '0;
  word_t connected_snapshot = '0;
  bit [31:0] connected_events = 0;
  time connected_time = 0;
  realtime connected_realtime = 0.0;
  `include "t_fourstate_resolve_common.vh"

  function automatic word_t pattern(input int offset);
    word_t result;
    for (int bitno = 0; bitno < WIDTH; bitno++) result[bitno] = state_code((bitno + offset) % 4);
    return result;
  endfunction

  function automatic word_t stimulus(input int phase);
    case (phase)
      0, 9: return '1;
      1: return 'x;
      2, 10: return 'z;
      3, 11: return '0;
      4: return pattern(0);
      5: return pattern(1);
      6: return pattern(2);
      7, 8: return pattern(3);
      default: return 'x;
    endcase
  endfunction

  wire [WIDTH-1:0] zero_omitted;
  default_zero #(WIDTH) u_zero_omitted(.o(zero_omitted));
  wire [WIDTH-1:0] zero_open;
  default_zero #(WIDTH) u_zero_open(.i(), .o(zero_open));
  wire [WIDTH-1:0] zero_connected;
  default_zero #(WIDTH) u_zero_connected(.i(source), .o(zero_connected));
  wire [WIDTH-1:0] one_omitted;
  default_one #(WIDTH) u_one_omitted(.o(one_omitted));
  wire [WIDTH-1:0] one_open;
  default_one #(WIDTH) u_one_open(.i(), .o(one_open));
  wire [WIDTH-1:0] one_connected;
  default_one #(WIDTH) u_one_connected(.i(source), .o(one_connected));
  wire [WIDTH-1:0] mixed_x_omitted;
  default_mixed_x #(WIDTH) u_mixed_x_omitted(.o(mixed_x_omitted));
  wire [WIDTH-1:0] mixed_x_open;
  default_mixed_x #(WIDTH) u_mixed_x_open(.i(), .o(mixed_x_open));
  wire [WIDTH-1:0] mixed_x_connected;
  default_mixed_x #(WIDTH) u_mixed_x_connected(.i(source), .o(mixed_x_connected));
  wire [WIDTH-1:0] mixed_z_omitted;
  default_mixed_z #(WIDTH) u_mixed_z_omitted(.o(mixed_z_omitted));
  wire [WIDTH-1:0] mixed_z_open;
  default_mixed_z #(WIDTH) u_mixed_z_open(.i(), .o(mixed_z_open));
  wire [WIDTH-1:0] mixed_z_connected;
  default_mixed_z #(WIDTH) u_mixed_z_connected(.i(source), .o(mixed_z_connected));

  // All connected instances must override their defaults even for driven Z.
  // One external observer checks mask-only changes and repeated source values.
  always @(mixed_x_connected) begin
    if (armed) begin
      connected_events++;
      connected_time = $time;
      connected_realtime = $realtime;
      connected_snapshot = mixed_x_connected;
    end
  end

  initial begin
    word_t wanted, previous;
    bit [31:0] wanted_events;
    time wanted_time;
    realtime wanted_realtime;
    previous = '0;
    wanted_events = 0;
    wanted_time = 0;
    wanted_realtime = 0.0;
    #1;
    `checkh(zero_omitted, {WIDTH{1'b0}});
    `checkh(zero_open, {WIDTH{1'b0}});
    `checkh(zero_connected, {WIDTH{1'b0}});
    `checkh(one_omitted, {WIDTH{1'b1}});
    `checkh(one_open, {WIDTH{1'b1}});
    `checkh(one_connected, {WIDTH{1'b0}});
    `checkh(mixed_x_omitted, pattern(2));
    `checkh(mixed_x_open, pattern(2));
    `checkh(mixed_x_connected, {WIDTH{1'b0}});
    `checkh(mixed_z_omitted, pattern(3));
    `checkh(mixed_z_open, pattern(3));
    `checkh(mixed_z_connected, {WIDTH{1'b0}});
    armed = 1;
    #0.125;
    for (int phase = 0; phase < 12; phase++) begin
      wanted = stimulus(phase);
      source = wanted;
      if (wanted !== previous) begin
        wanted_events++;
        wanted_time = $time;
        wanted_realtime = $realtime;
      end
      #0.001;
      `checkh(zero_omitted, {WIDTH{1'b0}});
      `checkh(zero_open, {WIDTH{1'b0}});
      `checkh(zero_connected, wanted);
      `checkh(one_omitted, {WIDTH{1'b1}});
      `checkh(one_open, {WIDTH{1'b1}});
      `checkh(one_connected, wanted);
      `checkh(mixed_x_omitted, pattern(2));
      `checkh(mixed_x_open, pattern(2));
      `checkh(mixed_x_connected, wanted);
      `checkh(mixed_z_omitted, pattern(3));
      `checkh(mixed_z_open, pattern(3));
      `checkh(mixed_z_connected, wanted);
      `checkh(source, wanted);
      `checkh(connected_snapshot, wanted);
      `checkd(connected_events, wanted_events);
      `checkd(connected_time, wanted_time);
      `checkr(connected_realtime, wanted_realtime);
      previous = wanted;
      #0.124;
    end
    done = 1;
  end
endmodule

// Literal defaults avoid reliance on a separate default-value parameter.
module default_zero #(parameter int WIDTH = 1)
    (input wire [WIDTH-1:0] i = {WIDTH{1'b0}},
     output wire [WIDTH-1:0] o);
  assign o = i;
endmodule

module default_one #(parameter int WIDTH = 1)
    (input wire [WIDTH-1:0] i = {WIDTH{1'b1}},
     output wire [WIDTH-1:0] o);
  assign o = i;
endmodule

module default_mixed_x #(parameter int WIDTH = 1)
    (input wire [WIDTH-1:0] i = WIDTH'(129'bx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx),
     output wire [WIDTH-1:0] o);
  assign o = i;
endmodule

module default_mixed_z #(parameter int WIDTH = 1)
    (input wire [WIDTH-1:0] i = WIDTH'(129'bzx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10zx10z),
     output wire [WIDTH-1:0] o);
  assign o = i;
endmodule
