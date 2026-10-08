// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkr(gotv,expv) do begin checks++; if ((gotv) != (expv)) begin $write("%%Error: %s:%0d: got=%0.3f expected=%0.3f\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [7:0] done;
  pull_check #(1) w1(done[0]);
  pull_check #(7) w7(done[1]);
  pull_check #(33) w33(done[2]);
  pull_check #(65) w65(done[3]);
  pull_check #(95) w95(done[4]);
  pull_check #(129) w129(done[5]);
  pull_check #(7, 3, 9) ascending(done[6]);
  pull_check #(33, 40, 8) nonzero(done[7]);
  wire distinct_done;
  distinct_pull distinct(distinct_done);
  wire constants_done;
  constant_pull constants(constants_done);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #6;
    if (done !== '1) $fatal(1, "Pull release checks did not finish");
    if (!distinct_done) $fatal(1, "Distinct pull checks did not finish");
    if (!constants_done) $fatal(1, "Constant pull checks did not finish");
    $display("Pull release checks: %0d", w1.checks + w7.checks + w33.checks
             + w65.checks + w95.checks + w129.checks + ascending.checks + nonzero.checks
             + distinct.checks + constants.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module constant_pull(output bit done = 0);
  // Preserve the four public constant-override controls. In particular,
  // runtime value assertions must also have valid scalar VCD encoding.
  tri0 declaration_one = 1'b1;
  tri1 declaration_zero = 1'b0;
  tri0 assignment_one;
  tri1 assignment_zero;
  assign assignment_one = 1'b1;
  assign assignment_zero = 1'b0;
  bit [31:0] checks = 0;

  initial begin
    #1;
    `checkh(declaration_one, 1'b1);
    `checkh(declaration_zero, 1'b0);
    `checkh(assignment_one, 1'b1);
    `checkh(assignment_zero, 1'b0);
    done = 1;
  end
endmodule

module distinct_pull(output bit done = 0);
  // Different RHS signals in the same scope must retain separate captured
  // value and X/Z halves. Staggering the changes also checks retained values.
  typedef logic [64:0] word_t;
  word_t source_a = '0, source_b = '0;
  tri0 word_t down;
  assign down = source_a;
  tri1 word_t up = source_b;
  word_t down_snapshot = '0, up_snapshot = '0;
  bit armed = 0;
  bit [31:0] checks = 0, down_events = 0, up_events = 0;
  time down_time = 0, up_time = 0;
  realtime down_realtime = 0.0, up_realtime = 0.0;

  always @(down) begin
    if (armed) begin
      down_events++;
      down_time = $time;
      down_realtime = $realtime;
      down_snapshot = down;
    end
  end
  always @(up) begin
    if (armed) begin
      up_events++;
      up_time = $time;
      up_realtime = $realtime;
      up_snapshot = up;
    end
  end

  function automatic word_t stimulus(input int phase, input bit second);
    word_t result;
    case (phase)
      0, 5, 6: result = second ? 'x : 'z;
      1, 7: result = second ? 'z : 'x;
      2: result = second ? '0 : '1;
      3: begin
        for (int bitno = 0; bitno < 65; bitno++) begin
          case ((bitno + (second ? 2 : 0)) % 4)
            0: result[bitno] = 1'b0;
            1: result[bitno] = 1'b1;
            2: result[bitno] = 1'bx;
            3: result[bitno] = 1'bz;
          endcase
        end
      end
      4: result = second ? '1 : '0;
      default: result = 'x;
    endcase
    return result;
  endfunction

  function automatic word_t resolve_pull(input word_t source, input bit pull_value);
    word_t result;
    for (int bitno = 0; bitno < 65; bitno++) begin
      if (source[bitno] === 1'bz) result[bitno] = pull_value;
      else result[bitno] = source[bitno];
    end
    return result;
  endfunction

  initial begin
    word_t want_down, want_up, previous_down, previous_up;
    bit [31:0] count_down, count_up;
    time want_down_time, want_up_time;
    realtime want_down_realtime, want_up_realtime;
    previous_down = '0;
    previous_up = '0;
    count_down = 0;
    count_up = 0;
    want_down_time = 0;
    want_up_time = 0;
    want_down_realtime = 0.0;
    want_up_realtime = 0.0;
    #1;
    armed = 1;
    #0.125;
    for (int phase = 0; phase < 8; phase++) begin
      for (int stage = 0; stage < 2; stage++) begin
        if (stage == 0) source_a = stimulus(phase, 0);
        else source_b = stimulus(phase, 1);
        want_down = resolve_pull(source_a, 0);
        want_up = resolve_pull(source_b, 1);
        if (want_down !== previous_down) begin
          count_down++;
          want_down_time = $time;
          want_down_realtime = $realtime;
        end
        if (want_up !== previous_up) begin
          count_up++;
          want_up_time = $time;
          want_up_realtime = $realtime;
        end
        #0.001;
        `checkh(down, want_down);
        `checkh(up, want_up);
        `checkh(down_snapshot, want_down);
        `checkh(up_snapshot, want_up);
        `checkd(down_events, count_down);
        `checkd(up_events, count_up);
        `checkd(down_time, want_down_time);
        `checkd(up_time, want_up_time);
        `checkr(down_realtime, want_down_realtime);
        `checkr(up_realtime, want_up_realtime);
        `checkd($isunknown(down), $isunknown(want_down));
        `checkd($isunknown(up), $isunknown(want_up));
        previous_down = want_down;
        previous_up = want_up;
        if (stage == 0) #0.049;
        else #0.074;
      end
    end
    done = 1;
  end
endmodule

module pull_check #(parameter WIDTH = 7, LEFT = WIDTH-1, RIGHT = 0)
                   (output bit done = 0);
  // Both continuous-assignment spellings use the default strong drive.
  // These are local whole packed nets, each with exactly one driver.
  typedef logic [LEFT:RIGHT] word_t;
  word_t driver = '0;
  tri0 word_t down;
  assign down = driver;
  tri1 word_t up = driver;
  tri0 word_t default_down;
  tri1 word_t default_up;
  word_t down_snapshot = '0, up_snapshot = '0;
  bit armed = 0;
  bit [31:0] checks = 0, down_events = 0, up_events = 0;
  time down_time = 0, up_time = 0;
  realtime down_realtime = 0.0, up_realtime = 0.0;

  always @(down) begin
    if (armed) begin
      down_events++;
      down_time = $time;
      down_realtime = $realtime;
      down_snapshot = down;
    end
  end
  always @(up) begin
    if (armed) begin
      up_events++;
      up_time = $time;
      up_realtime = $realtime;
      up_snapshot = up;
    end
  end

  function automatic word_t stimulus(input int phase);
    logic [WIDTH-1:0] packed_bits;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      case (phase)
        0, 4, 16, 25, 31: packed_bits[bitno] = 1'b0;
        1, 6, 30: packed_bits[bitno] = 1'b1;
        2, 8, 24: packed_bits[bitno] = 1'bx;
        3, 5, 7, 9, 10, 23, 29: packed_bits[bitno] = 1'bz;
        11, 12, 13, 14, 15, 26, 27: begin
          case ((bitno + ((phase >= 12 && phase <= 15)
                         ? (phase == 15 ? 3 : phase-11) : 0)) % 4)
            0: packed_bits[bitno] = 1'b0;
            1: packed_bits[bitno] = 1'b1;
            2: packed_bits[bitno] = 1'bx;
            3: packed_bits[bitno] = 1'bz;
          endcase
        end
        17, 19, 20: packed_bits[bitno] = bitno == WIDTH-1 ? 1'bz : 1'b0;
        18: packed_bits[bitno] = bitno == WIDTH-1 ? 1'bx : 1'b0;
        21: packed_bits[bitno] = 1'(bitno == WIDTH-1);
        22: packed_bits[bitno] = 1'b0;
        28: packed_bits[bitno] = 1'(bitno % 3 == 1);
        default: packed_bits[bitno] = 1'bx;
      endcase
    end
    return packed_bits;
  endfunction

  function automatic word_t resolve_pull(input word_t source, input bit pull_value);
    logic [WIDTH-1:0] packed_bits, resolved_bits;
    packed_bits = source;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      // Case equality distinguishes release Z from an actively driven X.
      if (packed_bits[bitno] === 1'bz) resolved_bits[bitno] = pull_value;
      else resolved_bits[bitno] = packed_bits[bitno];
    end
    return resolved_bits;
  endfunction

  initial begin
    word_t source, want_down, want_up, previous_down, previous_up;
    bit [31:0] count_down, count_up;
    time want_down_time, want_up_time;
    realtime want_down_realtime, want_up_realtime;
    previous_down = '0;
    previous_up = '0;
    count_down = 0;
    count_up = 0;
    want_down_time = 0;
    want_up_time = 0;
    want_down_realtime = 0.0;
    want_up_realtime = 0.0;
    // Ignore startup scheduling. Drive at a later tick, then observe after
    // one full precision step so neither continuous assignment nor observer
    // races with the checker. Fractional times also check $realtime.
    #1;
    armed = 1;
    #0.125;
    for (int phase = 0; phase < 32; phase++) begin
      source = stimulus(phase);
      want_down = resolve_pull(source, 0);
      want_up = resolve_pull(source, 1);
      if (want_down !== previous_down) begin
        count_down++;
        want_down_time = $time;
        want_down_realtime = $realtime;
      end
      if (want_up !== previous_up) begin
        count_up++;
        want_up_time = $time;
        want_up_realtime = $realtime;
      end
      driver = source;
      #0.001;
      `checkh(down, want_down);
      `checkh(up, want_up);
      `checkh(down_snapshot, want_down);
      `checkh(up_snapshot, want_up);
      `checkd($isunknown(down), $isunknown(want_down));
      `checkd($isunknown(up), $isunknown(want_up));
      `checkd(down_events, count_down);
      `checkd(up_events, count_up);
      `checkd(down_time, want_down_time);
      `checkd(up_time, want_up_time);
      `checkr(down_realtime, want_down_realtime);
      `checkr(up_realtime, want_up_realtime);
      `checkh(default_down, {WIDTH{1'b0}});
      `checkh(default_up, {WIDTH{1'b1}});
      `checkh(driver, source);
      previous_down = want_down;
      previous_up = want_up;
      #0.124;
    end
    done = 1;
  end
endmodule
