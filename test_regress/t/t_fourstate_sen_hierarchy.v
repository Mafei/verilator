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
// verilog_format: on

module sensitivity_bank #(
    parameter int WIDTH = 7
) (
    input bit instance_id,
    output bit done = 0,
    output int unsigned checks = 0
);
  logic [WIDTH-1:0] words [1:3];
  logic signed [3:0] index = 1;
  logic choose = 0;
  bit clk = 0;
  bit armed = 0;
  int unsigned direct_hits = 0;
  int unsigned iff_hits = 0;
  logic [WIDTH-1:0] selected = 0;
  logic [WIDTH-1:0] conditional_value = 0;
  logic [WIDTH-1:0] first_value;
  logic [WIDTH-1:0] second_value;
  logic [WIDTH-1:0] third_value;
  logic [WIDTH-1:0] expected;

  always @(index or words[index]) begin
    if (armed) begin
      direct_hits++;
      selected = words[index];
    end
  end
  always @(choose ? words[index] : words[1]) begin
    if (armed) conditional_value = choose ? words[index] : words[1];
  end
`ifdef IFF_EXPLICIT_CONTROL
  always @(posedge clk) begin
    if (words[index]) iff_hits++;
  end
`else
  always @(posedge clk iff words[index]) iff_hits++;
`endif

  initial begin
    first_value = (WIDTH'(1) << (WIDTH - 1)) | WIDTH'(int'(instance_id) + 2);
    second_value = first_value ^ WIDTH'('h15);
    third_value = first_value ^ WIDTH'('h2a);
    words[1] = first_value;
    words[2] = second_value;
    words[3] = third_value;
    #(int'(instance_id) + 1);
    armed = 1;
    expected = second_value ^ WIDTH'(1);
    words[2] = expected;
    #1;
    `checkd(direct_hits, 0);
    index = 2;
    #1;
    `checkd(direct_hits, 1);
    `checkh(selected, expected);
    choose = 1;
    #1;
    `checkh(conditional_value, expected);
    expected[1] = 1'bx;
    words[2][1] = 1'bx;
    #1;
    `checkd(direct_hits, 2);
    `checkh(selected, expected);
    `checkh(conditional_value, expected);
    clk = 1;
    #1;
    `checkd(iff_hits, 1);
    clk = 0;
    #1;
    expected[1] = 1'bz;
    words[2][1] = 1'bz;
    #1;
    `checkd(direct_hits, 3);
    `checkh(selected, expected);
    `checkh(conditional_value, expected);
    index = -1;
    #1;
    `checkd(direct_hits, 4);
    `checkh(selected, {WIDTH{1'bx}});
    `checkh(conditional_value, {WIDTH{1'bx}});
    clk = 1;
    #1;
    `checkd(iff_hits, 1);
    clk = 0;
    #1;
    index = 'x;
    #1;
    `checkd(direct_hits, 5);
    `checkh(selected, {WIDTH{1'bx}});
    `checkh(conditional_value, {WIDTH{1'bx}});
    clk = 1;
    #1;
    `checkd(iff_hits, 1);
    clk = 0;
    #1;
    index = 'z;
    #1;
    `checkd(direct_hits, 6);
    `checkh(selected, {WIDTH{1'bx}});
    `checkh(conditional_value, {WIDTH{1'bx}});
    clk = 1;
    #1;
    `checkd(iff_hits, 1);
    clk = 0;
    #1;
    index = 3;
    #1;
    `checkd(direct_hits, 7);
    `checkh(selected, third_value);
    `checkh(conditional_value, third_value);
    clk = 1;
    #1;
    `checkd(iff_hits, 2);
    clk = 0;
    #1;
    choose = 0;
    #1;
    `checkh(conditional_value, first_value);
    words[3] = 0;
    #1;
    `checkd(direct_hits, 8);
    `checkh(selected, WIDTH'(0));
    `checkh(conditional_value, first_value);
    clk = 1;
    #1;
    `checkd(iff_hits, 2);
    done = 1;
  end
endmodule

module t;
  wire [7:0] done;
  wire [31:0] bank_checks [0:7];
  int unsigned checks = 0;
  int unsigned total_checks = 0;

  for (genvar instance_number = 0; instance_number < 2; instance_number++) begin : instances
    for (genvar slot = 0; slot < 4; slot++) begin : widths
      localparam int WIDTH = slot == 0 ? 7 : slot == 1 ? 33 : slot == 2 ? 65 : 95;
      sensitivity_bank #(.WIDTH(WIDTH)) bank (
          .instance_id(1'(instance_number)),
          .done(done[instance_number * 4 + slot]),
          .checks(bank_checks[instance_number * 4 + slot])
      );
    end
  end

  initial begin
    // Exact deadline: every bank completes before 26ps; a lost event cannot hide in a wait.
    #40;
    `checkh(done, 8'hff);
    for (int bank_number = 0; bank_number < 8; bank_number++) begin
      total_checks += bank_checks[bank_number];
    end
    `checkd(total_checks, 256);
    $display("Sensitivity hierarchy checks: %0d", total_checks + checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
