// DESCRIPTION: Verilator: Complete signed/unsigned domains for indexed four-state reads
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define checkv(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: W=%0d round=%0d case=%0d got=%b expected=%b\n", `__FILE__, `__LINE__, WIDTH, round, kind, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [3:0] done;
  wire [31:0] total_checks = w7.checks + w33.checks + w65.checks + w95.checks;
  slice_width #(7) w7(done[0]);
  slice_width #(33) w33(done[1]);
  slice_width #(65) w65(done[2]);
  slice_width #(95) w95(done[3]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, w7.r_s4, w7.r_u4, w7.r_s32, w7.r_u32, w7.r_s64, w7.r_u64, w7.r_s95, w7.r_u95, w7.m_s4, w7.m_u4, w7.m_s32, w7.m_u32, w7.m_s64, w7.m_u64, w7.m_s95, w7.m_u95, w33.r_s4, w33.r_u4, w33.r_s32, w33.r_u32, w33.r_s64, w33.r_u64, w33.r_s95, w33.r_u95, w33.m_s4, w33.m_u4, w33.m_s32, w33.m_u32, w33.m_s64, w33.m_u64, w33.m_s95, w33.m_u95, w65.r_s4, w65.r_u4, w65.r_s32, w65.r_u32, w65.r_s64, w65.r_u64, w65.r_s95, w65.r_u95, w65.m_s4, w65.m_u4, w65.m_s32, w65.m_u32, w65.m_s64, w65.m_u64, w65.m_s95, w65.m_u95, w95.r_s4, w95.r_u4, w95.r_s32, w95.r_u32, w95.r_s64, w95.r_u64, w95.r_s95, w95.r_u95, w95.m_s4, w95.m_u4, w95.m_s32, w95.m_u32, w95.m_s64, w95.m_u64, w95.m_s95, w95.m_u95);
    wait (done === '1);
    #1;
    $display("Slice domain checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module slice_width #(parameter int WIDTH = 7)(output bit done = 0);
  logic [WIDTH-1:0] data;
  wire [WIDTH+3:4] shifted = data;
  // The ascending declaration is intentional range-normalization coverage.
  // verilator lint_off ASCRANGE
  wire [0:WIDTH-1] ascending = data;
  // verilator lint_on ASCRANGE
  logic signed [3:0] s4;
  logic [3:0] u4;
  logic signed [31:0] s32;
  logic [31:0] u32;
  logic signed [63:0] s64;
  logic [63:0] u64;
  logic signed [94:0] s95;
  logic [94:0] u95;
  int unsigned checks = 0;
  int unsigned calls[0:5];
  int round;
  int kind;
  int expected_lsb[0:7];
  logic [2:0] got;

  // Wide and narrow indices intentionally retain their complete source domains.
  // verilator lint_off WIDTHTRUNC
  // verilator lint_off WIDTHEXPAND
  wire [2:0] r_s4 = data[s4+:3];
  wire [2:0] r_u4 = data[u4+:3];
  wire [2:0] r_s32 = data[s32+:3];
  wire [2:0] r_u32 = data[u32+:3];
  wire [2:0] r_s64 = data[s64+:3];
  wire [2:0] r_u64 = data[u64+:3];
  wire [2:0] r_s95 = data[s95+:3];
  wire [2:0] r_u95 = data[u95+:3];
  wire [2:0] m_s4 = data[s4-:3];
  wire [2:0] m_u4 = data[u4-:3];
  wire [2:0] m_s32 = data[s32-:3];
  wire [2:0] m_u32 = data[u32-:3];
  wire [2:0] m_s64 = data[s64-:3];
  wire [2:0] m_u64 = data[u64-:3];
  wire [2:0] m_s95 = data[s95-:3];
  wire [2:0] m_u95 = data[u95-:3];
  // verilator lint_on WIDTHEXPAND
  // verilator lint_on WIDTHTRUNC

  function automatic logic signed [31:0] next_s32;
    calls[0]++;
    return s32;
  endfunction

  function automatic logic [31:0] next_u32;
    calls[1]++;
    return u32;
  endfunction

  function automatic logic signed [63:0] next_s64;
    calls[2]++;
    return s64;
  endfunction

  function automatic logic [63:0] next_u64;
    calls[3]++;
    return u64;
  endfunction

  function automatic logic signed [94:0] next_s95;
    calls[4]++;
    return s95;
  endfunction

  function automatic logic [94:0] next_u95;
    calls[5]++;
    return u95;
  endfunction

  // The reference addresses each requested destination bit independently.
  // Huge and unknown test indices use an explicit disjoint expected coordinate.
  function automatic logic [2:0] reference(input int lsb);
    for (int bitno = 0; bitno < 3; bitno++) begin
      if (lsb + bitno < 0 || lsb + bitno >= WIDTH) reference[bitno] = 1'bx;
      else reference[bitno] = data[lsb + bitno];
    end
  endfunction

  task automatic prepare_case;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      case ((bitno + round + kind) % 4)
        0: data[bitno] = 1'b0;
        1: data[bitno] = 1'b1;
        2: data[bitno] = 1'bx;
        3: data[bitno] = 1'bz;
      endcase
    end
    foreach (calls[i]) calls[i] = 0;
    foreach (expected_lsb[i]) expected_lsb[i] = WIDTH + 10;
    s4 = 0; u4 = 0; s32 = 0; u32 = 0; s64 = 0; u64 = 0; s95 = 0; u95 = 0;
    case (kind)
      0: foreach (expected_lsb[i]) expected_lsb[i] = 0;
      1: begin
        s4 = -1; u4 = 15;
        s32 = -1; u32 = '1; s64 = -1; u64 = '1; s95 = -1; u95 = '1;
        expected_lsb[0] = -1; expected_lsb[1] = 15;
        expected_lsb[2] = -1; expected_lsb[4] = -1; expected_lsb[6] = -1;
      end
      2: begin
        s4 = 7; u4 = 15;
        s32 = WIDTH - 2; u32 = WIDTH - 2; s64 = 64'(WIDTH - 2); u64 = 64'(WIDTH - 2);
        s95 = 95'(WIDTH - 2); u95 = 95'(WIDTH - 2);
        foreach (expected_lsb[i]) expected_lsb[i] = WIDTH - 2;
        expected_lsb[0] = 7; expected_lsb[1] = 15;
      end
      3: begin
        s4 = -2; u4 = 14;
        s32 = -2; u32 = 32'hfffffffe;
        s64 = -2; u64 = 64'hfffffffffffffffe;
        s95 = -2; u95 = 95'h7ffffffffffffffffffffffe;
        expected_lsb[0] = -2; expected_lsb[1] = 14;
        expected_lsb[2] = -2; expected_lsb[4] = -2; expected_lsb[6] = -2;
      end
      4: begin
        s4 = -3; u4 = 8;
        s32 = 32'sh80000000; u32 = 32'h80000000;
        s64 = 64'sh8000000000000000; u64 = 64'h100000000;
        s95 = {1'b1, 94'b0}; u95 = 95'd1 << 64;
        expected_lsb[0] = -3; expected_lsb[1] = 8;
      end
      5: begin
        s4 = 7; u4 = 15;
        s32 = 32'sh7fffffff; u32 = '1;
        s64 = 64'sh7fffffffffffffff; u64 = '1;
        s95 = {1'b0, {94{1'b1}}}; u95 = '1;
        expected_lsb[0] = 7; expected_lsb[1] = 15;
      end
      6: begin
        s4 = 'x; u4 = 'x; s32 = 'x; u32 = 'x; s64 = 'x; u64 = 'x; s95 = 'x; u95 = 'x;
      end
      7: begin
        s4 = 'z; u4 = 'z; s32 = 'z; u32 = 'z;
        s64 = -1; s64[63] = 1'bz; u64 = 1; u64[63] = 1'bx;
        s95 = -1; s95[94] = 1'bz; u95 = 1; u95[94] = 1'bx;
      end
      8: begin
        s4 = 1; u4 = 8;
        s32 = 31; u32 = 31; s64 = 31; u64 = 31; s95 = 31; u95 = 31;
        foreach (expected_lsb[i]) expected_lsb[i] = 31;
        expected_lsb[0] = 1; expected_lsb[1] = 8;
      end
      9: begin
        s4 = 3; u4 = 3; s32 = 3; u32 = 3; s64 = 3; u64 = 3; s95 = 3; u95 = 3;
        foreach (expected_lsb[i]) expected_lsb[i] = 3;
      end
    endcase
  endtask

  initial begin
    for (round = 0; round < 2; round++) begin
      for (kind = 0; kind < 10; kind++) begin
        prepare_case();
        #1;
        `checkv(r_s4, reference(expected_lsb[0]));
        `checkv(r_u4, reference(expected_lsb[1]));
        `checkv(r_s32, reference(expected_lsb[2]));
        `checkv(r_u32, reference(expected_lsb[3]));
        `checkv(r_s64, reference(expected_lsb[4]));
        `checkv(r_u64, reference(expected_lsb[5]));
        `checkv(r_s95, reference(expected_lsb[6]));
        `checkv(r_u95, reference(expected_lsb[7]));
        `checkv(m_s4, reference(expected_lsb[0] - 2));
        `checkv(m_u4, reference(expected_lsb[1] - 2));
        `checkv(m_s32, reference(expected_lsb[2] - 2));
        `checkv(m_u32, reference(expected_lsb[3] - 2));
        `checkv(m_s64, reference(expected_lsb[4] - 2));
        `checkv(m_u64, reference(expected_lsb[5] - 2));
        `checkv(m_s95, reference(expected_lsb[6] - 2));
        `checkv(m_u95, reference(expected_lsb[7] - 2));
        // Index functions must run once, shared by value and X/Z lowering.
        // verilator lint_off WIDTHTRUNC
        // verilator lint_off WIDTHEXPAND
        got = data[next_s32()+:3];
        `checkv(got, reference(expected_lsb[2]));
        `checkv(calls[0], 1);
        got = data[next_u32()+:3];
        `checkv(got, reference(expected_lsb[3]));
        `checkv(calls[1], 1);
        got = data[next_s64()+:3];
        `checkv(got, reference(expected_lsb[4]));
        `checkv(calls[2], 1);
        got = data[next_u64()+:3];
        `checkv(got, reference(expected_lsb[5]));
        `checkv(calls[3], 1);
        got = data[next_s95()+:3];
        `checkv(got, reference(expected_lsb[6]));
        `checkv(calls[4], 1);
        got = data[next_u95()+:3];
        `checkv(got, reference(expected_lsb[7]));
        `checkv(calls[5], 1);
        got = data[next_s32()-:3];
        `checkv(got, reference(expected_lsb[2] - 2));
        `checkv(calls[0], 2);
        got = data[next_u32()-:3];
        `checkv(got, reference(expected_lsb[3] - 2));
        `checkv(calls[1], 2);
        got = data[next_s64()-:3];
        `checkv(got, reference(expected_lsb[4] - 2));
        `checkv(calls[2], 2);
        got = data[next_u64()-:3];
        `checkv(got, reference(expected_lsb[5] - 2));
        `checkv(calls[3], 2);
        got = data[next_s95()-:3];
        `checkv(got, reference(expected_lsb[6] - 2));
        `checkv(calls[4], 2);
        got = data[next_u95()-:3];
        `checkv(got, reference(expected_lsb[7] - 2));
        `checkv(calls[5], 2);
        got = shifted[s32+:3];
        `checkv(got, reference(expected_lsb[2] - 4));
        got = shifted[s32-:3];
        `checkv(got, reference(expected_lsb[2] - 6));
        got = ascending[s32+:3];
        `checkv(got, reference(WIDTH - 3 - expected_lsb[2]));
        got = ascending[s32-:3];
        `checkv(got, reference(WIDTH - 1 - expected_lsb[2]));
        got = shifted[u32+:3];
        `checkv(got, reference(expected_lsb[3] - 4));
        got = shifted[u32-:3];
        `checkv(got, reference(expected_lsb[3] - 6));
        got = ascending[u32+:3];
        `checkv(got, reference(WIDTH - 3 - expected_lsb[3]));
        got = ascending[u32-:3];
        `checkv(got, reference(WIDTH - 1 - expected_lsb[3]));
        // verilator lint_on WIDTHEXPAND
        // verilator lint_on WIDTHTRUNC
        $display("SLICE READ W=%0d round=%0d case=%0d t=%0t r_s4=%b r_u4=%b r_s32=%b r_u32=%b r_s64=%b r_u64=%b r_s95=%b r_u95=%b m_s4=%b m_u4=%b m_s32=%b m_u32=%b m_s64=%b m_u64=%b m_s95=%b m_u95=%b", WIDTH, round, kind, $time, r_s4, r_u4, r_s32, r_u32, r_s64, r_u64, r_s95, r_u95, m_s4, m_u4, m_s32, m_u32, m_s64, m_u64, m_s95, m_u95);
        #1;
      end
    end
    done = 1;
  end
endmodule
