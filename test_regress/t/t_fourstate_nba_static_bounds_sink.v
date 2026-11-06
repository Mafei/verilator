// DESCRIPTION: Verilator: Static class-task delayed invalid writes retain side effects
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define STRINGIFY(x) `"x`"
// verilog_format: on
module t;
  timeunit 1ns; timeprecision 1ps;
  logic [7:0] bank[0:1];
  wire [7:0] bank0 = bank[0];
  wire [7:0] bank1 = bank[1];
  int rhs_calls = 0;
  int delay_calls = 0;
  int checks = 0;
  function automatic logic [7:0] capture_rhs(input logic [7:0] value);
    ++rhs_calls;
    return value;
  endfunction
  function automatic int delay_ticks();
    ++delay_calls;
    return 2;
  endfunction
  class Writer;
    static task schedule(input int index, input logic [7:0] value);
      t.bank[index] <= #(t.delay_ticks()) t.capture_rhs(value);
    endtask
  endclass
  initial begin
    bank[0] = '0;
    bank[1] = '0;
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, bank0, bank1);
    Writer::schedule(0, 8'b10xz01z1);
    Writer::schedule(-1, 8'b11110000);
    Writer::schedule(1, 8'bz10x1100);
    Writer::schedule(2, 8'bxxxxxxxx);
    if (rhs_calls != 4) $fatal(1, "RHS side effects must run once per assignment");
    ++checks;
    if (delay_calls != 4) $fatal(1, "delay side effects must run once per assignment");
    ++checks;
    if (bank[0] !== '0) $fatal(1, "narrow valid target committed early");
    ++checks;
    if (bank[1] !== '0) $fatal(1, "second valid target committed early");
    ++checks;
    #1ns;
    if (bank[0] !== '0) $fatal(1, "first target changed before NBA delay");
    ++checks;
    if (bank[1] !== '0) $fatal(1, "second target changed before NBA delay");
    ++checks;
    #2ns;
    if (bank[0] !== 8'b10xz01z1) $fatal(1, "first delayed value/xz lost");
    ++checks;
    if (bank[1] !== 8'bz10x1100) $fatal(1, "second delayed value/xz lost or invalid write leaked");
    ++checks;
    if (rhs_calls != 4) $fatal(1, "RHS side effects repeated during commit");
    ++checks;
    if (delay_calls != 4) $fatal(1, "delay side effects repeated during commit");
    ++checks;
    $display("STATIC_CLASS_NBA_BOUNDS_PASS checks=%0d", checks);
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
