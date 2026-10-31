// DESCRIPTION: Verilator: Four-state skewed clocking output support boundary
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

interface sender_if (input wire clk, output wire [6:0] bus);
  timeunit 1ns;
  timeprecision 1ps;
  clocking cb @(posedge clk);
    output #1step bus;
  endclocking
  task automatic drive(input logic [6:0] value);
    cb.bus <= value;
    @(cb);
  endtask
endinterface

module t;
  timeunit 1ns;
  timeprecision 1ps;
  bit clk = 0;
  wire [6:0] bus;
  sender_if sender (clk, bus);
  always #5ns clk = ~clk;
  initial begin
    sender.drive(7'b10xz101);
    #2ps;
    $display("%b", bus);
    $finish;
  end
endmodule
