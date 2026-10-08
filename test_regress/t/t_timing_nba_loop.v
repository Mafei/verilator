// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [6:0] done;
  nba_original original(done[0]);
  nba_repeated repeated(done[6]);
  nba_width #(7) w7(done[1]);
  nba_width #(33) w33(done[2]);
  nba_width #(65) w65(done[3]);
  nba_width #(95) w95(done[4]);
  nba_width #(129) w129(done[5]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, original.out, repeated.repeat_out, w33.looped, w33.captured, w33.ordered,
              w33.ordered_rev, w33.different, w33.nested, w33.disjoint,
              w33.q_same, w33.q_due);
    #250;
    if (done !== '1) $fatal(1, "Delayed NBA checks did not finish");
    $display("NBA checks: %0d", original.checks + repeated.checks + w7.checks + w33.checks
             + w65.checks + w95.checks + w129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module nba_original(output bit done = 0);
`ifdef NBA_FOURSTATE
  logic [31:0] out;
`else
  bit [31:0] out = 32'hc35a0000;
`endif
  bit [35:0] init_value = 36'h056785678;
  bit [31:0] loops = 0;
  bit [31:0] index;
  bit init_mem = 0;
  bit [31:0] checks = 0;
  time changed = 0;

  always @(out) changed = $time;
  always @(posedge init_mem) begin
    for (index = 0; index < loops; index++)
      out[index] <= #100 1'(init_value >> index);
  end
  initial begin
    #1 loops = 16;
    #99 init_mem = 1;
    #100 init_mem = 0;
  end
  initial begin
    #199;
    `checkd($time, 64'd199);
`ifdef NBA_FOURSTATE
    `checkh(out, 32'hxxxxxxxx);
`else
    `checkh(out, 32'hc35a0000);
`endif
    #2;
    `checkd($time, 64'd201);
    `checkd(changed, 64'd200);
`ifdef NBA_FOURSTATE
    `checkh(out, 32'hxxxx5678);
`else
    `checkh(out, 32'hc35a5678);
`endif
    done = 1;
  end
endmodule

module nba_repeated(output bit done = 0);
`ifdef NBA_FOURSTATE
  typedef logic [15:0] payload_t;
  logic [31:0] repeat_out;
`else
  typedef bit [15:0] payload_t;
  bit [31:0] repeat_out = 32'h5ac30000;
`endif
  payload_t payload;
  bit pulse = 0;
  bit [31:0] delay_ticks;
  bit [31:0] index;
  bit [31:0] calls = 0;
  bit [31:0] checks = 0;
  time changed = 0;

  function automatic payload_t selected_word();
    calls++;
    return payload;
  endfunction
  always @(repeat_out) changed = $time;
  always @(posedge pulse) begin
    for (index = 0; index < 16; index++)
      repeat_out[index] <= #(delay_ticks) 1'(selected_word() >> index);
  end
  initial begin
    #40;
    payload = 16'ha5c3;
    delay_ticks = 10;
    pulse = 1;
    #1;
    pulse = 0;
    payload = '1;
    #1;
`ifdef NBA_FOURSTATE
    payload = 16'h3cz1;
`else
    payload = 16'h3c91;
`endif
    delay_ticks = 8;
    pulse = 1;
    #1;
    pulse = 0;
    payload = '0;
    #1;
    payload = 16'h0f0f;
    delay_ticks = 4;
    pulse = 1;
    #1;
    pulse = 0;
    payload = '1;
  end
  initial begin
    #47;
    `checkd($time, 64'd47);
`ifdef NBA_FOURSTATE
    `checkh(repeat_out, 32'hxxxxxxxx);
`else
    `checkh(repeat_out, 32'h5ac30000);
`endif
    #2;
    `checkd(changed, 64'd48);
`ifdef NBA_FOURSTATE
    `checkh(repeat_out, 32'hxxxx0f0f);
`else
    `checkh(repeat_out, 32'h5ac30f0f);
`endif
    #2;
    `checkd(changed, 64'd50);
`ifdef NBA_FOURSTATE
    `checkh(repeat_out, 32'hxxxx3cz1);
`else
    `checkh(repeat_out, 32'h5ac33c91);
`endif
    `checkd(calls, 32'd48);
    done = 1;
  end
endmodule

module nba_width #(parameter WIDTH = 7) (output bit done = 0);
  // Cross a 32-bit boundary where possible, while keeping the select in range.
  localparam bit [31:0] CAPTURE_INDEX = WIDTH == 7 ? 2 : (WIDTH == 95 ? 63 : WIDTH - 3);
`ifdef NBA_FOURSTATE
  typedef logic [WIDTH-1:0] word_t;
`else
  typedef bit [WIDTH-1:0] word_t;
`endif
  word_t looped, captured, ordered, ordered_rev, different, nested, disjoint;
  word_t q_same, q_due;
  word_t source_loop, source_rhs;
  word_t seed, expected_loop, expected_capture, expected_order, expected_different;
  word_t expected_disjoint, scheduled_word;
  bit [31:0] index = 0;
  bit [31:0] index_calls = 0;
  bit [31:0] rhs_calls = 0;
  bit [31:0] checks = 0;
  time looped_changed = 0, captured_changed = 0, ordered_changed = 0;
  time ordered_rev_changed = 0, different_changed = 0, nested_changed = 0;
  time disjoint_changed = 0, q_same_changed = 0, q_due_changed = 0;

  function automatic word_t pattern(input bit [31:0] kind);
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      if (kind == 3) pattern[bitno] = (bitno % 3) == 1;
      else begin
        case (bitno % 4)
`ifdef NBA_FOURSTATE
          0: case (kind)
            0: pattern[bitno] = 1'bx;
            1: pattern[bitno] = 1'bz;
            default: pattern[bitno] = 1'b1;
          endcase
          1: pattern[bitno] = kind == 0 ? 1'bz : 1'bx;
          2: pattern[bitno] = kind == 2 ? 1'bz : 1'(kind);
`else
          0: pattern[bitno] = kind != 0;
          1: pattern[bitno] = kind != 1;
          2: pattern[bitno] = kind == 1;
`endif
          3: pattern[bitno] = kind == 0;
        endcase
      end
    end
  endfunction
  function automatic bit [31:0] selected_index();
    index_calls++;
    return index;
  endfunction
  function automatic word_t selected_rhs();
    rhs_calls++;
    return source_rhs;
  endfunction
  task automatic check_word(input word_t value, input word_t wanted);
    `checkh(value, wanted);
    `checkh($isunknown(value), $isunknown(wanted));
  endtask

  always @(looped) looped_changed = $time;
  always @(captured) captured_changed = $time;
  always @(ordered) ordered_changed = $time;
  always @(ordered_rev) ordered_rev_changed = $time;
  always @(different) different_changed = $time;
  always @(nested) nested_changed = $time;
  always @(disjoint) disjoint_changed = $time;
  always @(q_same) q_same_changed = $time;
  always @(q_due) q_due_changed = $time;

  initial begin
    seed = pattern(0);
    looped = seed;
    captured = seed;
    ordered = seed;
    ordered_rev = seed;
    different = seed;
    nested = seed;
    disjoint = seed;
    q_same = seed;
    q_due = seed;
    source_loop = pattern(1);
    source_rhs = pattern(1);
    expected_loop = seed;
    expected_capture = seed;
    for (int bitno = 0; bitno < WIDTH - 2; bitno++)
      expected_loop[bitno] = source_loop[bitno];
    for (int bitno = CAPTURE_INDEX; bitno < CAPTURE_INDEX + 3; bitno++)
      expected_capture[bitno] = source_rhs[bitno];
    #1;
    for (index = 0; index < WIDTH - 2; index++)
      looped[index] <= #4 1'(source_loop >> index);
    index = CAPTURE_INDEX;
    captured[selected_index() +: 3] <= #7 3'(selected_rhs() >> index);
    `checkd(index_calls, 32'd1);
    `checkd(rhs_calls, 32'd1);
    index = 0;
    source_loop = pattern(2);
    source_rhs = pattern(2);
    #3;
    check_word(looped, seed);
    #2;
    check_word(looped, expected_loop);
    `checkd(looped_changed, 64'd5);
    #1;
    check_word(captured, seed);
    #2;
    check_word(captured, expected_capture);
    `checkd(captured_changed, 64'd8);
    `checkd(index_calls, 32'd1);
    `checkd(rhs_calls, 32'd1);

    // One procedural writer establishes the order at the common expiry time.
    scheduled_word = pattern(1);
    expected_order = scheduled_word;
    ordered <= #3 scheduled_word;
`ifdef NBA_FOURSTATE
    expected_order[WIDTH-1 -: 3] = 3'bzx1;
    expected_order[0] = 1'bx;
    ordered[WIDTH-1 -: 3] <= #3 3'bzx1;
    ordered[0] <= #3 1'bz;
    ordered[0] <= #3 1'bx;
    ordered_rev[WIDTH-1 -: 3] <= #3 3'bzx1;
`else
    expected_order[WIDTH-1 -: 3] = 3'b010;
    expected_order[0] = 1'b0;
    ordered[WIDTH-1 -: 3] <= #3 3'b010;
    ordered[0] <= #3 1'b1;
    ordered[0] <= #3 1'b0;
    ordered_rev[WIDTH-1 -: 3] <= #3 3'b111;
`endif
    ordered_rev <= #3 pattern(3);
    scheduled_word = pattern(2);
    #2;
    check_word(ordered, seed);
    check_word(ordered_rev, seed);
    #2;
    check_word(ordered, expected_order);
    check_word(ordered_rev, pattern(3));
    `checkd(ordered_changed, 64'd12);
    `checkd(ordered_rev_changed, 64'd12);

    // The later launch expires first. Pending assignments must not be cancelled.
    expected_different = seed;
`ifdef NBA_FOURSTATE
    different[0] <= #4 1'bx;
    different[0] <= #2 1'bz;
`else
    different[0] <= #4 1'b0;
    different[0] <= #2 1'b1;
`endif
    #1;
    check_word(different, seed);
    #2;
`ifdef NBA_FOURSTATE
    expected_different[0] = 1'bz;
`else
    expected_different[0] = 1'b1;
`endif
    check_word(different, expected_different);
    `checkd(different_changed, 64'd15);
    #2;
`ifdef NBA_FOURSTATE
    expected_different[0] = 1'bx;
`else
    expected_different[0] = 1'b0;
`endif
    check_word(different, expected_different);
    `checkd(different_changed, 64'd17);

    // Forked writers touch disjoint bits. No winner is assumed across processes
    // for overlapping writes. Source/index mutations occur after both captures.
    index = CAPTURE_INDEX;
    index_calls = 0;
    rhs_calls = 0;
    source_rhs = pattern(1);
    expected_disjoint = seed;
    expected_disjoint[WIDTH-1] = 1'b1;
`ifdef NBA_FOURSTATE
    expected_disjoint[0] = 1'bz;
`else
    expected_disjoint[0] = 1'b1;
`endif
    fork
      begin
        fork
          begin
            nested[selected_index() +: 3] <= #3 3'(selected_rhs() >> index);
          end
        join
      end
      begin
        disjoint[WIDTH-1] <= #3 1'b1;
      end
      begin
`ifdef NBA_FOURSTATE
        disjoint[0] <= #3 1'bz;
`else
        disjoint[0] <= #3 1'b1;
`endif
      end
      begin
        #1;
        index = 0;
        source_rhs = pattern(2);
      end
    join
    `checkd(index_calls, 32'd1);
    `checkd(rhs_calls, 32'd1);
    #1;
    check_word(nested, seed);
    check_word(disjoint, seed);
    #2;
    check_word(nested, expected_capture);
    check_word(disjoint, expected_disjoint);
    `checkd(nested_changed, 64'd21);
    `checkd(disjoint_changed, 64'd21);
    `checkd(index_calls, 32'd1);
    `checkd(rhs_calls, 32'd1);

    // These assignments are all whole words, with overlapping pending lifetimes.
    q_same <= #6 pattern(1);
    q_due <= #6 pattern(1);
    #1;
    q_same <= #5 pattern(2);
    q_due <= #3 pattern(3);
    #2;
    check_word(q_same, seed);
    check_word(q_due, seed);
    #2;
    check_word(q_same, seed);
    check_word(q_due, pattern(3));
    `checkd(q_due_changed, 64'd26);
    #2;
    check_word(q_same, pattern(2));
    check_word(q_due, pattern(1));
    `checkd(q_same_changed, 64'd28);
    `checkd(q_due_changed, 64'd28);
    done = 1;
  end
endmodule
