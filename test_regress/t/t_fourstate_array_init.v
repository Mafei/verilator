// DESCRIPTION: Verilator: Keep array-index snapshots across split C functions
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b exp=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0)
`define STRINGIFY_(value) `"value`"
`define STRINGIFY(value) `STRINGIFY_(value)
// verilog_format: on

`ifndef ARRAY_INIT_WIDTH
`define ARRAY_INIT_WIDTH 7
`endif
`ifndef TEST_DUMPFILE
`define TEST_DUMPFILE t_fourstate_array_init.vcd
`endif

`timescale 1ps/1ps
module t;
  localparam int WIDTH = `ARRAY_INIT_WIDTH;
  localparam logic [WIDTH - 1:0] FIRST = 'h11;
  localparam logic [WIDTH - 1:0] MIDDLE = 'h22;
  localparam logic [WIDTH - 1:0] LAST = 'h33;
  logic [WIDTH - 1:0] bank[3:1];
  wire [WIDTH - 1:0] bank1 = bank[1];
  wire [WIDTH - 1:0] bank2 = bank[2];
  wire [WIDTH - 1:0] bank3 = bank[3];
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, bank1, bank2, bank3);
    // The value and X/Z write must share the snapshot, even across generated C functions.
    bank[1] = FIRST;
    bank[2] = MIDDLE;
    bank[3] = LAST;
    #1;
    $display("ARRAY_INIT_FINAL width=%0d bank1=%b bank2=%b bank3=%b", WIDTH, bank1, bank2, bank3);
    `checkh(bank1, FIRST);
    `checkh(bank2, MIDDLE);
    `checkh(bank3, LAST);
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
