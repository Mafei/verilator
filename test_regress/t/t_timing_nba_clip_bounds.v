// DESCRIPTION: Verilator: Signed, unsigned and unknown event NBA part-select bounds
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: case=%0d got=%b expected=%b\n", `__FILE__, `__LINE__, kind, (gotv), (expv)); $stop; end end while (0);
// verilog_format: on

module t;
`ifdef PARTSELECT_FOURSTATE
  localparam int CASES = 22;
  logic [3:0] bank[0:1];
`else
  localparam int CASES = 16;
  bit [3:0] bank[0:1];
`endif
  int signed s32;
  longint signed s64;
  logic signed [94:0] s95;
  int unsigned u32;
  longint unsigned u64;
  logic [94:0] u95;
  logic [1:0] payload;
  int target;
  int kind;
  int checks = 0;
  int index_calls = 0;
  logic [3:0] expected;
  event update_event;

  function automatic int side_effect_index;
    index_calls++;
    return -1;
  endfunction

  initial begin
    for (kind = 0; kind < CASES; kind++) begin
      bank[0] = 4'b0110;
      bank[1] = 4'b1001;
      s32 = 0;
      s64 = 0;
      s95 = 0;
      u32 = 0;
      u64 = 0;
      u95 = 0;
      target = 0;
      payload = 2'b10;
      expected = 4'b0110;
      index_calls = 0;
      case (kind)
        0: begin s32 = -1; expected = 4'b0111; end
        1: s32 = -2;
        2: begin s32 = 3; payload = 2'b01; expected = 4'b1110; end
        3: s32 = 32'sh80000000;
        4: s32 = 32'sh7fffffff;
        5: u32 = '1;
        6: begin s64 = -1; expected = 4'b0111; end
        7: s64 = 64'sh8000000000000000;
        8: u64 = '1;
        9: begin s95 = -1; expected = 4'b0111; end
        10: s95 = {1'b1, 94'b0};
        11: u95 = '1;
        12: expected = 4'b0111;
        13: u64 = 64'hffffffff;
        14: s64 = -64'shffffffff;
        15: s95 = (95'd1 << 64) | 95'd1;
        16: s32 = 'x;
        17: s32 = 'z;
        18: s64 = 'x;
        19: s95 = 'z;
        20: u32 = 'x;
        21: u95 = 'z;
      endcase
      // Wide indices intentionally retain every bit for the bounds check.
      // verilator lint_off WIDTHTRUNC
      case (kind)
        0, 1, 2, 3, 4, 16, 17: bank[target][s32+:2] <= @update_event payload;
        5, 20: bank[target][u32+:2] <= @update_event payload;
        6, 7, 14, 18: bank[target][s64+:2] <= @update_event payload;
        8, 13: bank[target][u64+:2] <= @update_event payload;
        9, 10, 15, 19: bank[target][s95+:2] <= @update_event payload;
        11, 21: bank[target][u95+:2] <= @update_event payload;
        12: bank[target][side_effect_index()+:2] <= @update_event payload;
      endcase
      // verilator lint_on WIDTHTRUNC
      `checkh(index_calls, kind == 12 ? 1 : 0);
      // All bounds decisions and RHS/index snapshots precede these mutations.
      target = 1;
      s32 = 0;
      s64 = 0;
      s95 = 0;
      u32 = 0;
      u64 = 0;
      u95 = 0;
      payload = 0;
      `checkh(bank[0], 4'b0110);
      `checkh(bank[1], 4'b1001);
      #1;
      ->update_event;
      `checkh(bank[0], 4'b0110);
      `checkh(bank[1], 4'b1001);
      #0;
      `checkh(bank[0], 4'b0110);
      `checkh(bank[1], 4'b1001);
      $strobe("BOUNDS STROBE case=%0d t=%0t bank0=%b bank1=%b", kind, $time, bank[0], bank[1]);
      #1;
      `checkh(bank[0], expected);
      `checkh(bank[1], 4'b1001);
      #1;
    end
    $display("Part-select bounds checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
