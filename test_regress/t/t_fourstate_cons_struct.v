// DESCRIPTION: Verilator: Unpacked struct construction and member evaluation counts
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
// verilog_format: on

module t;
`ifdef CONS_STRUCT_XZ
  typedef logic [3:0] word_t;
  localparam word_t FIRST = 4'bx1z0;
  localparam word_t SECOND = 4'b0zx1;
`else
  typedef bit [3:0] word_t;
  localparam word_t FIRST = 4'b1001;
  localparam word_t SECOND = 4'b0011;
`endif
  typedef struct {
    word_t left;
    word_t right;
  } pair_t;
  typedef struct {
    pair_t pair;
    bit tag;
  } packet_t;
  packet_t packet;
  packet_t copied;
  bit [31:0] calls = 0;
  bit [31:0] checks = 0;

  function automatic word_t next_word(input word_t value);
    calls++;
    return value;
  endfunction

  initial begin
    packet = '{pair: '{left: next_word(FIRST), right: next_word(SECOND)}, tag: 1'b1};
    `checkh(calls, 32'd2);
    `checkh(packet.pair.left, FIRST);
    `checkh(packet.pair.right, SECOND);
    `checkh(packet.tag, 1'b1);
    copied = packet;
    packet.pair.left = '0;
    `checkh(copied.pair.left, FIRST);
    `checkh(copied.pair.right, SECOND);
    `checkh(copied.tag, 1'b1);
    `checkh(calls, 32'd2);
    $display("CONS_STRUCT_PASS checks=%0d calls=%0d copied=%b,%b tag=%b",
             checks, calls, copied.pair.left, copied.pair.right, copied.tag);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
