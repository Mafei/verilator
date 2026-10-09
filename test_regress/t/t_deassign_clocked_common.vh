// DESCRIPTION: Verilator: Deassign before an eligible clocked writer executes
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps / 1ps

module retention #(
    parameter int WIDTH = 1,
    parameter bit USE_NBA = 0
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  logic clock = 0;
  bit write_enable = 0;
  logic enable = 0;
  logic [WIDTH-1:0] q = 'x;
  logic [WIDTH-1:0] source = 'z;
  logic [WIDTH-1:0] written = '0;

  always @(enable) begin
    if (enable == 1'b1) assign q = source;
    else if (enable == 1'b0) deassign q;
  end

  generate
    if (USE_NBA) begin
      always @(posedge clock) begin
        if (write_enable) q <= written;
      end
    end
    else begin
      always @(posedge clock) begin
        if (write_enable) q = written;
      end
    end
  endgenerate

  task check_value(input logic [WIDTH-1:0] expected, input string tag);
    $display("RETENTION %0t width=%0d nba=%0d %s got=%b expected=%b", $time, WIDTH, USE_NBA, tag,
             q, expected);
    `checkh(q, expected)
  endtask

  initial begin
    #10;
    enable = 1;
    #1;
    check_value('z, "active_z");
    source = '1;
    #1;
    check_value('1, "active_one");
    // There has been no clock edge, and the conditional writer has not executed.
    enable = 0;
    #1;
    check_value('1, "deassign_before_writer");
    source = 'x;
    #1;
    check_value('1, "source_after_release");
    // An edge with a false guard is not a procedural assignment to q.
    clock = 1;
    #1;
    check_value('1, "inactive_writer");
    clock = 0;
    #1;
    write_enable = 1;
    clock = 1;
    #1;
    check_value('0, "first_actual_writer");
    clock = 0;
    enable = 1;
    #1;
    check_value('x, "active_x");
    write_enable = 0;
    clock = 1;
    #1;
    enable = 0;
    #1;
    check_value('x, "deassign_after_skipped_writer");
    clock = 0;
    written = 'z;
    #1;
    write_enable = 1;
    clock = 1;
    #1;
    check_value('z, "actual_z_writer");
    done = 1;
  end
endmodule

module t;
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
`ifdef ONLY_TWOSTATE
  wire [7:0] done;
`else
  wire [15:0] done;
`endif
`ifndef ONLY_TWOSTATE
  retention #(1, 0) b1 (done[8]);
  retention #(7, 0) b7 (done[9]);
  retention #(33, 0) b33 (done[10]);
  retention #(65, 0) b65 (done[11]);
  retention #(1, 1) n1 (done[12]);
  retention #(7, 1) n7 (done[13]);
  retention #(33, 1) n33 (done[14]);
  retention #(65, 1) n65 (done[15]);
`endif
  bit_retention #(1, 0) c1 (done[0]);
  bit_retention #(7, 0) c7 (done[1]);
  bit_retention #(33, 0) c33 (done[2]);
  bit_retention #(65, 0) c65 (done[3]);
  bit_retention #(1, 1) d1 (done[4]);
  bit_retention #(7, 1) d7 (done[5]);
  bit_retention #(33, 1) d33 (done[6]);
  bit_retention #(65, 1) d65 (done[7]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #40;
    `checkh(&done, 1'b1)
    $display(
        "Clocked deassign bit checks: %0d",
        c1.checks + c7.checks + c33.checks + c65.checks + d1.checks + d7.checks + d33.checks + d65.checks);
`ifndef ONLY_TWOSTATE
    $display(
        "Clocked deassign logic checks: %0d",
        b1.checks + b7.checks + b33.checks + b65.checks + n1.checks + n7.checks + n33.checks + n65.checks);
`endif
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule


module bit_retention #(
    parameter int WIDTH = 1,
    parameter bit USE_NBA = 0
) (
    output bit done = 0
);
  bit [31:0] checks = 0;
  `include "t_fourstate_drive_common.vh"
  bit clock = 0;
  bit write_enable = 0;
  bit enable = 0;
  bit [WIDTH-1:0] q = '0;
  bit [WIDTH-1:0] source = '1;
  bit [WIDTH-1:0] written = '0;
  always @(enable) begin
    if (enable) assign q = source;
    else deassign q;
  end
  generate
    if (USE_NBA) begin
      always @(posedge clock) if (write_enable) q <= written;
    end
    else begin
      always @(posedge clock) if (write_enable) q = written;
    end
  endgenerate
  task check_value(input bit [WIDTH-1:0] expected, input string tag);
    $display("BIT_RETENTION %0t width=%0d nba=%0d %s got=%b expected=%b", $time, WIDTH, USE_NBA,
             tag, q, expected);
    `checkh(q, expected)
  endtask
  initial begin
    #10;
    enable = 1;
    #1;
    check_value('1, "active_one");
    #1;
    enable = 0;
    #1;
    check_value('1, "deassign_before_writer");
    source = '0;
    #1;
    check_value('1, "source_after_release");
    clock = 1;
    #1;
    check_value('1, "inactive_writer");
    clock = 0;
    #1;
    write_enable = 1;
    clock = 1;
    #1;
    check_value('0, "first_actual_writer");
    clock = 0;
    source = '1;
    enable = 1;
    #1;
    check_value('1, "active_one_again");
    write_enable = 0;
    clock = 1;
    #1;
    enable = 0;
    #1;
    check_value('1, "deassign_after_skipped_writer");
    clock = 0;
    written = '1;
    #1;
    write_enable = 1;
    clock = 1;
    #1;
    check_value('1, "actual_one_writer");
    done = 1;
  end
endmodule
