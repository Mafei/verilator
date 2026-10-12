// DESCRIPTION: Event-controlled NBA unknown target indices and independent concat writes
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps/1ps
// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on
module t;
  event update;
  logic [6:0] bank[3:1];
  wire [6:0] bank1 = bank[1];
  wire [6:0] bank2 = bank[2];
  wire [6:0] bank3 = bank[3];
  logic [14:0] partial = 15'h3535;
  logic [6:0] other = 7'h23;
  logic [1:0] index = 2'b00;
  logic [3:0] base = 4'b0000;
  logic [6:0] rhs = '0;
  int checks = 0;
  int phase;
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, bank1, bank2, bank3, partial, other, index, base);
    foreach (bank[slot]) bank[slot] = 7'(slot * 'h11);
    #1;
    `checkh(bank1, 7'h11);
    `checkh(bank2, 7'h22);
    `checkh(bank3, 7'h33);
    for (phase = 0; phase < 2; phase++) begin
      #1;
      index = phase == 0 ? 2'bxx : 2'bzz;
      base = phase == 0 ? 4'bxxxx : 4'bzzzz;
      rhs = phase == 0 ? 7'bx01z101 : 7'bz10x010;
      bank[index] <= @update rhs;
      {partial[base+:7], other} <= @update {rhs, rhs};
      index = 2'b01;
      base = 4'b0001;
      rhs = 7'h0;
      #1;
      ->update;
      #1;
      `checkh(bank[1], 7'h11);
      `checkh(bank[2], 7'h22);
      `checkh(bank[3], 7'h33);
      `checkh(partial, 15'h3535);
      `checkh(other, phase == 0 ? 7'bx01z101 : 7'bz10x010);
    end
    $display("EVENT_NBA_UNKNOWN_PASS checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
