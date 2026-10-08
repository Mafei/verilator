// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

module t;
  `include "t_fourstate_resolve_common.vh"
  wire [5:0] done;
  event_width #(1) w1(done[0]);
  event_width #(7) w7(done[1]);
  event_width #(33) w33(done[2]);
  event_width #(65) w65(done[3]);
  event_width #(95) w95(done[4]);
  event_width #(129) w129(done[5]);
  wire [6:0] packet_done;
  packet_width #(1) p1(packet_done[0]);
  packet_width #(17) p17(packet_done[1]);
  packet_width #(24) p24(packet_done[2]);
  packet_width #(31) p31(packet_done[3]);
  packet_width #(32) p32(packet_done[4]);
  packet_width #(63) p63(packet_done[5]);
  packet_width #(64) p64(packet_done[6]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #5;
    if (done !== '1 || packet_done !== '1) $fatal(1, "Event checks did not finish");
    $display("Resolver event checks: %0d", w1.checks + w7.checks + w33.checks + w65.checks + w95.checks + w129.checks);
    $display("Resolver packet checks: %0d", p1.checks + p17.checks + p24.checks + p31.checks + p32.checks + p63.checks + p64.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module event_width #(parameter int WIDTH = 1)(output bit done = 0);
  typedef logic [WIDTH-1:0] word_t;
  word_t source_a2 = 'z, source_b2 = 'z;
  word_t source_a3 = 'z, source_b3 = 'z, source_c3 = 'z;
  bit [31:0] checks = 0;
  bit armed = 0;
  `include "t_fourstate_resolve_common.vh"

  function automatic word_t pattern(input int offset);
    word_t value;
    for (int bitno = 0; bitno < WIDTH; bitno++) value[bitno] = state_code((bitno + offset) % 4);
    return value;
  endfunction

  // Pure RHS calls preserve X/Z. Their arguments belong to distinct nets.
  // Evaluation count is not observable and is not claimed by this test.
  function automatic word_t permute(input word_t value);
    word_t result;
    for (int bitno = 0; bitno < WIDTH; bitno++) result[bitno] = value[WIDTH-1-bitno];
    return result;
  endfunction

  function automatic word_t expected_pair(input int kind, input word_t a, input word_t b);
    word_t result;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      result[bitno] = pair_literal(kind, state_index(a[bitno]) * 4 + state_index(b[bitno]));
    end
    return result;
  endfunction

  function automatic word_t expected_triple(input int kind, input word_t a,
                                          input word_t b, input word_t c);
    word_t result;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      result[bitno] = triple_literal(kind, state_index(a[bitno]) * 16
                                    + state_index(b[bitno]) * 4 + state_index(c[bitno]));
    end
    return result;
  endfunction

  // Expected sources are independent of the driven variables under test.
  function automatic word_t source_expected(input int phase, input int source);
    case (source)
      0, 2: case (phase)
        0, 1, 2: return '0;
        3, 4, 6, 7: return 'z;
        5, 8: return 'x;
        9, 10, 11: return '1;
        12, 13, 14: return pattern(0);
        15: begin
          if (source == 0) return 'z;
          return pattern(0);
        end
        default: return 'x;
      endcase
      1, 3: case (phase)
        0, 4, 5, 6, 11, 12: return 'z;
        1, 2, 3: return '1;
        7, 8, 9, 10: return '0;
        13: return pattern(1);
        14, 15: begin
          if (source == 1) return 'z;
          return pattern(1);
        end
        default: return 'x;
      endcase
      4: begin
        if (phase == 14) return pattern(2);
        return 'z;
      end
      default: return 'x;
    endcase
  endfunction

  wire word_t r2_wire;
  assign r2_wire = source_a2;
  assign r2_wire = permute(source_b2);
  word_t r2_wire_snapshot = 'z;
  bit [31:0] r2_wire_events = 0;
  time r2_wire_time = 0;
  realtime r2_wire_realtime = 0.0;
  word_t r2_wire_previous = 'z, r2_wire_wanted;
  bit [31:0] r2_wire_count = 0;
  time r2_wire_want_time = 0;
  realtime r2_wire_want_realtime = 0.0;
  always @(r2_wire) begin
    if (armed) begin
      r2_wire_events++;
      r2_wire_time = $time;
      r2_wire_realtime = $realtime;
      r2_wire_snapshot = r2_wire;
    end
  end

  tri word_t r2_tri;
  assign r2_tri = source_a2;
  assign r2_tri = permute(source_b2);
  word_t r2_tri_snapshot = 'z;
  bit [31:0] r2_tri_events = 0;
  time r2_tri_time = 0;
  realtime r2_tri_realtime = 0.0;
  word_t r2_tri_previous = 'z, r2_tri_wanted;
  bit [31:0] r2_tri_count = 0;
  time r2_tri_want_time = 0;
  realtime r2_tri_want_realtime = 0.0;
  always @(r2_tri) begin
    if (armed) begin
      r2_tri_events++;
      r2_tri_time = $time;
      r2_tri_realtime = $realtime;
      r2_tri_snapshot = r2_tri;
    end
  end

  wor word_t r2_wor;
  assign r2_wor = source_a2;
  assign r2_wor = permute(source_b2);
  word_t r2_wor_snapshot = 'z;
  bit [31:0] r2_wor_events = 0;
  time r2_wor_time = 0;
  realtime r2_wor_realtime = 0.0;
  word_t r2_wor_previous = 'z, r2_wor_wanted;
  bit [31:0] r2_wor_count = 0;
  time r2_wor_want_time = 0;
  realtime r2_wor_want_realtime = 0.0;
  always @(r2_wor) begin
    if (armed) begin
      r2_wor_events++;
      r2_wor_time = $time;
      r2_wor_realtime = $realtime;
      r2_wor_snapshot = r2_wor;
    end
  end

  wand word_t r2_wand;
  assign r2_wand = source_a2;
  assign r2_wand = permute(source_b2);
  word_t r2_wand_snapshot = 'z;
  bit [31:0] r2_wand_events = 0;
  time r2_wand_time = 0;
  realtime r2_wand_realtime = 0.0;
  word_t r2_wand_previous = 'z, r2_wand_wanted;
  bit [31:0] r2_wand_count = 0;
  time r2_wand_want_time = 0;
  realtime r2_wand_want_realtime = 0.0;
  always @(r2_wand) begin
    if (armed) begin
      r2_wand_events++;
      r2_wand_time = $time;
      r2_wand_realtime = $realtime;
      r2_wand_snapshot = r2_wand;
    end
  end

  wire word_t r3_wire;
  assign r3_wire = source_a3;
  assign r3_wire = permute(source_b3);
  assign r3_wire = source_c3;
  word_t r3_wire_snapshot = 'z;
  bit [31:0] r3_wire_events = 0;
  time r3_wire_time = 0;
  realtime r3_wire_realtime = 0.0;
  word_t r3_wire_previous = 'z, r3_wire_wanted;
  bit [31:0] r3_wire_count = 0;
  time r3_wire_want_time = 0;
  realtime r3_wire_want_realtime = 0.0;
  always @(r3_wire) begin
    if (armed) begin
      r3_wire_events++;
      r3_wire_time = $time;
      r3_wire_realtime = $realtime;
      r3_wire_snapshot = r3_wire;
    end
  end

  tri word_t r3_tri;
  assign r3_tri = source_a3;
  assign r3_tri = permute(source_b3);
  assign r3_tri = source_c3;
  word_t r3_tri_snapshot = 'z;
  bit [31:0] r3_tri_events = 0;
  time r3_tri_time = 0;
  realtime r3_tri_realtime = 0.0;
  word_t r3_tri_previous = 'z, r3_tri_wanted;
  bit [31:0] r3_tri_count = 0;
  time r3_tri_want_time = 0;
  realtime r3_tri_want_realtime = 0.0;
  always @(r3_tri) begin
    if (armed) begin
      r3_tri_events++;
      r3_tri_time = $time;
      r3_tri_realtime = $realtime;
      r3_tri_snapshot = r3_tri;
    end
  end

  wor word_t r3_wor;
  assign r3_wor = source_a3;
  assign r3_wor = permute(source_b3);
  assign r3_wor = source_c3;
  word_t r3_wor_snapshot = 'z;
  bit [31:0] r3_wor_events = 0;
  time r3_wor_time = 0;
  realtime r3_wor_realtime = 0.0;
  word_t r3_wor_previous = 'z, r3_wor_wanted;
  bit [31:0] r3_wor_count = 0;
  time r3_wor_want_time = 0;
  realtime r3_wor_want_realtime = 0.0;
  always @(r3_wor) begin
    if (armed) begin
      r3_wor_events++;
      r3_wor_time = $time;
      r3_wor_realtime = $realtime;
      r3_wor_snapshot = r3_wor;
    end
  end

  wand word_t r3_wand;
  assign r3_wand = source_a3;
  assign r3_wand = permute(source_b3);
  assign r3_wand = source_c3;
  word_t r3_wand_snapshot = 'z;
  bit [31:0] r3_wand_events = 0;
  time r3_wand_time = 0;
  realtime r3_wand_realtime = 0.0;
  word_t r3_wand_previous = 'z, r3_wand_wanted;
  bit [31:0] r3_wand_count = 0;
  time r3_wand_want_time = 0;
  realtime r3_wand_want_realtime = 0.0;
  always @(r3_wand) begin
    if (armed) begin
      r3_wand_events++;
      r3_wand_time = $time;
      r3_wand_realtime = $realtime;
      r3_wand_snapshot = r3_wand;
    end
  end

  initial begin
    word_t want_a2, want_b2, want_a3, want_b3, want_c3;
    #1;
    armed = 1;
    #0.125;
    for (int phase = 0; phase < 16; phase++) begin
      // Each step updates one contribution per independent resolver.
      case (phase)
        0: begin source_a2 = '0; source_a3 = '0; end
        1, 2: begin source_b2 = '1; source_b3 = '1; end
        3, 6: begin source_a2 = 'z; source_a3 = 'z; end
        4, 11: begin source_b2 = 'z; source_b3 = 'z; end
        5, 8: begin source_a2 = 'x; source_a3 = 'x; end
        7: begin source_b2 = '0; source_b3 = '0; end
        9, 10: begin source_a2 = '1; source_a3 = '1; end
        12: begin source_a2 = pattern(0); source_a3 = pattern(0); end
        13: begin source_b2 = pattern(1); source_b3 = pattern(1); end
        14: begin source_b2 = 'z; source_c3 = pattern(2); end
        15: begin source_a2 = 'z; source_c3 = 'z; end
      endcase
      want_a2 = source_expected(phase, 0);
      want_b2 = source_expected(phase, 1);
      want_a3 = source_expected(phase, 2);
      want_b3 = source_expected(phase, 3);
      want_c3 = source_expected(phase, 4);
      r2_wire_wanted = expected_pair(0, want_a2, permute(want_b2));
      if (r2_wire_wanted !== r2_wire_previous) begin
        r2_wire_count++;
        r2_wire_want_time = $time;
        r2_wire_want_realtime = $realtime;
      end
      r2_tri_wanted = expected_pair(0, want_a2, permute(want_b2));
      if (r2_tri_wanted !== r2_tri_previous) begin
        r2_tri_count++;
        r2_tri_want_time = $time;
        r2_tri_want_realtime = $realtime;
      end
      r2_wor_wanted = expected_pair(1, want_a2, permute(want_b2));
      if (r2_wor_wanted !== r2_wor_previous) begin
        r2_wor_count++;
        r2_wor_want_time = $time;
        r2_wor_want_realtime = $realtime;
      end
      r2_wand_wanted = expected_pair(2, want_a2, permute(want_b2));
      if (r2_wand_wanted !== r2_wand_previous) begin
        r2_wand_count++;
        r2_wand_want_time = $time;
        r2_wand_want_realtime = $realtime;
      end
      r3_wire_wanted = expected_triple(0, want_a3, permute(want_b3), want_c3);
      if (r3_wire_wanted !== r3_wire_previous) begin
        r3_wire_count++;
        r3_wire_want_time = $time;
        r3_wire_want_realtime = $realtime;
      end
      r3_tri_wanted = expected_triple(0, want_a3, permute(want_b3), want_c3);
      if (r3_tri_wanted !== r3_tri_previous) begin
        r3_tri_count++;
        r3_tri_want_time = $time;
        r3_tri_want_realtime = $realtime;
      end
      r3_wor_wanted = expected_triple(1, want_a3, permute(want_b3), want_c3);
      if (r3_wor_wanted !== r3_wor_previous) begin
        r3_wor_count++;
        r3_wor_want_time = $time;
        r3_wor_want_realtime = $realtime;
      end
      r3_wand_wanted = expected_triple(2, want_a3, permute(want_b3), want_c3);
      if (r3_wand_wanted !== r3_wand_previous) begin
        r3_wand_count++;
        r3_wand_want_time = $time;
        r3_wand_want_realtime = $realtime;
      end
      #0.001;
      `checkh(r2_wire, r2_wire_wanted);
      `checkh(r2_wire_snapshot, r2_wire_wanted);
      `checkd(r2_wire_events, r2_wire_count);
      `checkd(r2_wire_time, r2_wire_want_time);
      `checkr(r2_wire_realtime, r2_wire_want_realtime);
      r2_wire_previous = r2_wire_wanted;
      `checkh(r2_tri, r2_tri_wanted);
      `checkh(r2_tri_snapshot, r2_tri_wanted);
      `checkd(r2_tri_events, r2_tri_count);
      `checkd(r2_tri_time, r2_tri_want_time);
      `checkr(r2_tri_realtime, r2_tri_want_realtime);
      r2_tri_previous = r2_tri_wanted;
      `checkh(r2_wor, r2_wor_wanted);
      `checkh(r2_wor_snapshot, r2_wor_wanted);
      `checkd(r2_wor_events, r2_wor_count);
      `checkd(r2_wor_time, r2_wor_want_time);
      `checkr(r2_wor_realtime, r2_wor_want_realtime);
      r2_wor_previous = r2_wor_wanted;
      `checkh(r2_wand, r2_wand_wanted);
      `checkh(r2_wand_snapshot, r2_wand_wanted);
      `checkd(r2_wand_events, r2_wand_count);
      `checkd(r2_wand_time, r2_wand_want_time);
      `checkr(r2_wand_realtime, r2_wand_want_realtime);
      r2_wand_previous = r2_wand_wanted;
      `checkh(r3_wire, r3_wire_wanted);
      `checkh(r3_wire_snapshot, r3_wire_wanted);
      `checkd(r3_wire_events, r3_wire_count);
      `checkd(r3_wire_time, r3_wire_want_time);
      `checkr(r3_wire_realtime, r3_wire_want_realtime);
      r3_wire_previous = r3_wire_wanted;
      `checkh(r3_tri, r3_tri_wanted);
      `checkh(r3_tri_snapshot, r3_tri_wanted);
      `checkd(r3_tri_events, r3_tri_count);
      `checkd(r3_tri_time, r3_tri_want_time);
      `checkr(r3_tri_realtime, r3_tri_want_realtime);
      r3_tri_previous = r3_tri_wanted;
      `checkh(r3_wor, r3_wor_wanted);
      `checkh(r3_wor_snapshot, r3_wor_wanted);
      `checkd(r3_wor_events, r3_wor_count);
      `checkd(r3_wor_time, r3_wor_want_time);
      `checkr(r3_wor_realtime, r3_wor_want_realtime);
      r3_wor_previous = r3_wor_wanted;
      `checkh(r3_wand, r3_wand_wanted);
      `checkh(r3_wand_snapshot, r3_wand_wanted);
      `checkd(r3_wand_events, r3_wand_count);
      `checkd(r3_wand_time, r3_wand_want_time);
      `checkr(r3_wand_realtime, r3_wand_want_realtime);
      r3_wand_previous = r3_wand_wanted;
      `checkh(source_a2, want_a2);
      `checkh(source_b2, want_b2);
      `checkh(source_a3, want_a3);
      `checkh(source_b3, want_b3);
      `checkh(source_c3, want_c3);
      #0.124;
    end
    done = 1;
  end
endmodule

module packet_width #(parameter int WIDTH = 1)(output bit done = 0);
  typedef logic [WIDTH-1:0] word_t;
  bit [31:0] checks = 0;
  bit disabled_a = 1, disabled_b = 1;
  word_t source_a = '0, source_b = pattern();
  `include "t_fourstate_resolve_common.vh"
  function automatic word_t pattern();
    word_t value;
    for (int bitno = 0; bitno < WIDTH; bitno++) value[bitno] = state_code(bitno % 4);
    return value;
  endfunction
  function automatic word_t expected(input int kind, input word_t a, input word_t b);
    word_t value;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      value[bitno] = pair_literal(kind, state_index(a[bitno]) * 4 + state_index(b[bitno]));
    end
    return value;
  endfunction
  wire word_t resolved_wire;
  // Negated one-bit enables and wide complements exercise padding cleanup.
  assign resolved_wire = ~disabled_a ? ~source_a : 'z;
  assign resolved_wire = ~disabled_b ? source_b : 'z;
  tri word_t resolved_tri;
  // Negated one-bit enables and wide complements exercise padding cleanup.
  assign resolved_tri = ~disabled_a ? ~source_a : 'z;
  assign resolved_tri = ~disabled_b ? source_b : 'z;
  wor word_t resolved_wor;
  // Negated one-bit enables and wide complements exercise padding cleanup.
  assign resolved_wor = ~disabled_a ? ~source_a : 'z;
  assign resolved_wor = ~disabled_b ? source_b : 'z;
  wand word_t resolved_wand;
  // Negated one-bit enables and wide complements exercise padding cleanup.
  assign resolved_wand = ~disabled_a ? ~source_a : 'z;
  assign resolved_wand = ~disabled_b ? source_b : 'z;
  initial begin
    word_t want_a, want_b, contribution_a, contribution_b;
    bit want_disabled_a, want_disabled_b;
    #1;
    // First settle must preserve every Z bit, including packet bits above 32.
    `checkh(resolved_wire, {WIDTH{1'bz}});
    `checkh(resolved_tri, {WIDTH{1'bz}});
    `checkh(resolved_wor, {WIDTH{1'bz}});
    `checkh(resolved_wand, {WIDTH{1'bz}});
    #0.125;
    for (int phase = 0; phase < 8; phase++) begin
      case (phase)
        0: disabled_a = 0;
        1: source_a = '1;
        2: source_a = 'x;
        3: source_a = 'z;
        4: disabled_a = 1;
        5: disabled_b = 0;
        6: source_b = '1;
        7: disabled_b = 1;
      endcase
      case (phase)
        0: want_a = '0;
        1: want_a = '1;
        2: want_a = 'x;
        default: want_a = 'z;
      endcase
      if (phase < 6) want_b = pattern();
      else want_b = '1;
      want_disabled_a = (phase >= 4);
      want_disabled_b = (phase < 5 || phase == 7);
      if (want_disabled_a) contribution_a = 'z;
      else contribution_a = ~want_a;
      if (want_disabled_b) contribution_b = 'z;
      else contribution_b = want_b;
      #0.001;
      `checkh(resolved_wire, expected(0, contribution_a, contribution_b));
      `checkh(resolved_tri, expected(0, contribution_a, contribution_b));
      `checkh(resolved_wor, expected(1, contribution_a, contribution_b));
      `checkh(resolved_wand, expected(2, contribution_a, contribution_b));
      `checkh(source_a, want_a);
      `checkh(source_b, want_b);
      `checkd(disabled_a, want_disabled_a);
      `checkd(disabled_b, want_disabled_b);
      #0.124;
    end
    done = 1;
  end
endmodule
