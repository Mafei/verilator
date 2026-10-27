// DESCRIPTION: Verilator: Packed word slices retain full index domains
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: step=%0d domain=%0d kind=%0d got=%b expected=%b\n", `__FILE__, `__LINE__, step, domain, kind, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: step=%0d got=%0d expected=%0d\n", `__FILE__, `__LINE__, step, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  localparam logic [6:0] P7_0 = 7'b10xz001;
  localparam logic [6:0] P7_1 = 7'b0z110x1;
  localparam logic [6:0] P7_2 = 7'bz0011x0;
  localparam logic [6:0] P7_3 = 7'b011z0x1;
  localparam logic [6:0] P7_4 = 7'bx1010z0;
  localparam logic [6:0] P7_5 = 7'b110x1z0;
  localparam logic [32:0] P33_0 = {1'b1, {8{4'b01xz}}};
  localparam logic [32:0] P33_1 = {1'b0, {8{4'bz1x0}}};
  localparam logic [32:0] P33_2 = {1'bz, {8{4'b10zx}}};
  localparam logic [32:0] P33_3 = {1'bx, {8{4'b0z11}}};
  localparam logic [32:0] P33_4 = {1'b1, {8{4'bzx00}}};
  localparam logic [32:0] P33_5 = {1'b0, {8{4'bx1z1}}};

  logic [2:0][6:0] words7;
  logic [1:0][5:3][6:0] cube7;
  logic [5:3][32:0] shifted33;
  // The ascending middle dimension deliberately reverses word significance.
  // verilator lint_off ASCRANGE
  logic [1:0][3:5][32:0] cube33;
  // verilator lint_on ASCRANGE
  logic signed [31:0] s32[0:3];
  logic [31:0] u32[0:3];
  logic signed [63:0] s64[0:3];
  logic [63:0] u64[0:3];
  logic signed [94:0] s95[0:3];
  logic [94:0] u95[0:3];
  logic [13:0] r7 = '0;
  logic [13:0] m7 = '0;
  logic [65:0] r33 = '0;
  logic [65:0] m33 = '0;
  int checks = 0;
  int index_calls = 0;
  int step;
  int domain;
  int kind;
  int outer;
  bit phase;

  function automatic logic signed [94:0] next_signed95;
    index_calls++;
    return s95[0];
  endfunction

  task automatic prepare_payload;
    // Whole-array assignments keep payload creation independent of index lowering.
    // Descending dimensions put the highest word at the left of a concatenation.
    if (phase) begin
      words7 = {P7_5, P7_4, P7_3};
      shifted33 = {P33_5, P33_4, P33_3};
      cube7 = {P7_2, P7_1, P7_0, P7_5, P7_4, P7_3};
      cube33 = {P33_0, P33_1, P33_2, P33_3, P33_4, P33_5};
    end else begin
      words7 = {P7_2, P7_1, P7_0};
      shifted33 = {P33_2, P33_1, P33_0};
      cube7 = {P7_5, P7_4, P7_3, P7_2, P7_1, P7_0};
      cube33 = {P33_3, P33_4, P33_5, P33_0, P33_1, P33_2};
    end
  endtask

  task automatic prepare_indices;
    int coordinate[0:3];
    coordinate[0] = 1;
    coordinate[1] = 4;
    coordinate[2] = 4;
    coordinate[3] = 4;
    if (kind == 1) begin
      // Signed cases overlap the low bound; unsigned cases overlap the high bound.
      coordinate[0] = domain[0] ? 2 : -1;
      coordinate[1] = domain[0] ? 6 : 3;
      coordinate[2] = domain[0] ? 5 : 2;
      coordinate[3] = domain[0] ? 6 : 3;
    end
    for (int lane = 0; lane < 4; lane++) begin
      s32[lane] = coordinate[lane];
      u32[lane] = 32'(coordinate[lane]);
      s64[lane] = 64'(coordinate[lane]);
      u64[lane] = 64'(coordinate[lane]);
      s95[lane] = 95'(coordinate[lane]);
      u95[lane] = 95'(coordinate[lane]);
      if (kind == 2) begin
        s32[lane] = 32'sh80000000;
        u32[lane] = 32'hffffffff;
        s64[lane] = 64'sh0000000100000000;
        u64[lane] = 64'h0000000100000001;
        s95[lane] = -(95'd1 << 64);
        u95[lane] = (95'd1 << 64) + 95'd4;
      end else if (kind == 3) begin
        // Known low bits would select data if the unknown high bit were discarded.
        s32[lane] = 1; s32[lane][31] = 1'bx;
        u32[lane] = 4; u32[lane][31] = 1'bz;
        s64[lane] = 1; s64[lane][63] = 1'bx;
        u64[lane] = 4; u64[lane][63] = 1'bz;
        s95[lane] = 1; s95[lane][94] = 1'bx;
        u95[lane] = 4; u95[lane][94] = 1'bz;
      end
    end
  endtask

  initial begin
    logic [13:0] once7;
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, r7, m7, r33, m33);
    for (step = 0; step < 24; step++) begin
      domain = step / 4;
      kind = step % 4;
      phase = 1'(step);
      outer = (domain + kind) % 2;
      prepare_payload();
      prepare_indices();
      #1;
      // These wide index domains are intentional, including the 95-bit high bits.
      // verilator lint_off WIDTHTRUNC
      // verilator lint_off WIDTHEXPAND
      case (domain)
        0: begin
          r7 = words7[s32[0]+:2];
          m7 = cube7[outer][s32[1]-:2];
          r33 = shifted33[s32[2]+:2];
          m33 = cube33[outer][s32[3]-:2];
        end
        1: begin
          r7 = words7[u32[0]+:2];
          m7 = cube7[outer][u32[1]-:2];
          r33 = shifted33[u32[2]+:2];
          m33 = cube33[outer][u32[3]-:2];
        end
        2: begin
          r7 = words7[s64[0]+:2];
          m7 = cube7[outer][s64[1]-:2];
          r33 = shifted33[s64[2]+:2];
          m33 = cube33[outer][s64[3]-:2];
        end
        3: begin
          r7 = words7[u64[0]+:2];
          m7 = cube7[outer][u64[1]-:2];
          r33 = shifted33[u64[2]+:2];
          m33 = cube33[outer][u64[3]-:2];
        end
        4: begin
          r7 = words7[s95[0]+:2];
          m7 = cube7[outer][s95[1]-:2];
          r33 = shifted33[s95[2]+:2];
          m33 = cube33[outer][s95[3]-:2];
        end
        5: begin
          r7 = words7[u95[0]+:2];
          m7 = cube7[outer][u95[1]-:2];
          r33 = shifted33[u95[2]+:2];
          m33 = cube33[outer][u95[3]-:2];
        end
        default: `stop;
      endcase
      // verilator lint_on WIDTHEXPAND
      // verilator lint_on WIDTHTRUNC
      #1;
      // Expected results are explicit word concatenations, not flattened offsets.
      // A partly missing word is all X, while every bit of each present word survives.
      case (kind)
        0: begin
          `checkh(r7, (phase ? {P7_5, P7_4} : {P7_2, P7_1}));
          `checkh(m7, ((phase ^ 1'(outer)) ? {P7_4, P7_3} : {P7_1, P7_0}));
          `checkh(r33, (phase ? {P33_5, P33_4} : {P33_2, P33_1}));
          `checkh(m33, ((phase ^ 1'(outer)) ? {P33_3, P33_4} : {P33_0, P33_1}));
        end
        1: begin
          if (domain[0]) begin
            `checkh(r7, (phase ? {7'bx, P7_5} : {7'bx, P7_2}));
            `checkh(m7, ((phase ^ 1'(outer)) ? {7'bx, P7_5} : {7'bx, P7_2}));
            `checkh(r33, (phase ? {33'bx, P33_5} : {33'bx, P33_2}));
            `checkh(m33, ((phase ^ 1'(outer)) ? {P33_5, 33'bx} : {P33_2, 33'bx}));
          end else begin
            `checkh(r7, (phase ? {P7_3, 7'bx} : {P7_0, 7'bx}));
            `checkh(m7, ((phase ^ 1'(outer)) ? {P7_3, 7'bx} : {P7_0, 7'bx}));
            `checkh(r33, (phase ? {P33_3, 33'bx} : {P33_0, 33'bx}));
            `checkh(m33, ((phase ^ 1'(outer)) ? {33'bx, P33_3} : {33'bx, P33_0}));
          end
        end
        2, 3: begin
          `checkh(r7, 14'bx);
          `checkh(m7, 14'bx);
          `checkh(r33, 66'bx);
          `checkh(m33, 66'bx);
        end
        default: `stop;
      endcase
      if (domain == 4 && kind == 0) begin
        // verilator lint_off WIDTHTRUNC
        // verilator lint_off WIDTHEXPAND
        once7 = words7[next_signed95()+:2];
        // verilator lint_on WIDTHEXPAND
        // verilator lint_on WIDTHTRUNC
        `checkh(once7, (phase ? {P7_5, P7_4} : {P7_2, P7_1}));
        `checkd(index_calls, 1);
      end
      $display("PACKED SLICE step=%0d domain=%0d kind=%0d t=%0t r7=%b m7=%b r33=%b m33=%b",
               step, domain, kind, $time, r7, m7, r33, m33);
    end
    #1;
    $display("Packed slice checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
