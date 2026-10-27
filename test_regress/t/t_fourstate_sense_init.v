// DESCRIPTION: Verilator: Explicit four-state change-event initialization
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d exp=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
`define checkh(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%p exp=%p\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  bit never;
  logic [12:0] default_x;
  logic [12:0] declared_x = 'x;
  logic [12:0] declared_z = 'z;
  logic [12:0] known = '0;
  int default_n = 0;
  int default_s = 0;
  int x_n = 0;
  int x_s = 0;
  int z_n = 0;
  int z_s = 0;
  int known_n = 0;
  int known_s = 0;

  always @(default_x) default_n++;
  always @(default_x) begin
    default_s++;
    if (never) #1;
  end
  always @(declared_x) x_n++;
  always @(declared_x) begin
    x_s++;
    if (never) #1;
  end
  always @(declared_z) z_n++;
  always @(declared_z) begin
    z_s++;
    if (never) #1;
  end
  always @(known) known_n++;
  always @(known) begin
    known_s++;
    if (never) #1;
  end

  task snapshot(input int phase,
                input logic [12:0] want_default, want_x, want_z, want_known,
                input int want_default_count, want_x_count, want_z_count, want_known_count);
    `checkh(default_x, want_default);
    `checkh(declared_x, want_x);
    `checkh(declared_z, want_z);
    `checkh(known, want_known);
    `checkd(default_n, want_default_count);
    `checkd(default_s, want_default_count);
    `checkd(x_n, want_x_count);
    `checkd(x_s, want_x_count);
    `checkd(z_n, want_z_count);
    `checkd(z_s, want_z_count);
    `checkd(known_n, want_known_count);
    `checkd(known_s, want_known_count);
    $write("FOURSTATE_SENSE_INIT p=%0d default=%b/%0d/%0d x=%b/%0d/%0d z=%b/%0d/%0d known=%b/%0d/%0d\n",
           phase, default_x, default_n, default_s, declared_x, x_n, x_s,
           declared_z, z_n, z_s, known, known_n, known_s);
  endtask

  initial begin
    // Declaration initialization is static. There are no procedural time-zero writes.
    #1;
    snapshot(0, 13'bxxxxxxxxxxxxx, 13'bxxxxxxxxxxxxx, 13'bzzzzzzzzzzzzz,
             13'b0000000000000, 0, 0, 0, 0);
    default_x = 'x;
    declared_x = 'x;
    declared_z = 'z;
    known = '0;
    #1;
    snapshot(1, 13'bxxxxxxxxxxxxx, 13'bxxxxxxxxxxxxx, 13'bzzzzzzzzzzzzz,
             13'b0000000000000, 0, 0, 0, 0);

    // X and Z have the same mask. X and known1 have the same value part.
    default_x = 'z;
    declared_x = '1;
    declared_z = 'x;
    known = 13'b0000001000000;
    #1;
    snapshot(2, 13'bzzzzzzzzzzzzz, 13'b1111111111111, 13'bxxxxxxxxxxxxx,
             13'b0000001000000, 1, 1, 1, 1);
    default_x = 'x;
    declared_x = 'x;
    declared_z = 'z;
    known = 13'b000000x000000;
    #1;
    snapshot(3, 13'bxxxxxxxxxxxxx, 13'bxxxxxxxxxxxxx, 13'bzzzzzzzzzzzzz,
             13'b000000x000000, 2, 2, 2, 2);
    default_x = 'x;
    declared_x = 'x;
    declared_z = 'z;
    known = 13'b000000x000000;
    #1;
    snapshot(4, 13'bxxxxxxxxxxxxx, 13'bxxxxxxxxxxxxx, 13'bzzzzzzzzzzzzz,
             13'b000000x000000, 2, 2, 2, 2);

    // Mask-only changes outside the least-significant bit must still count.
    default_x = 13'b111111x111111;
    declared_x = 13'bxxxxxxxxxxxxz;
    declared_z = 13'bzzzzzz0zzzzzz;
    known = '0;
    #1;
    snapshot(5, 13'b111111x111111, 13'bxxxxxxxxxxxxz, 13'bzzzzzz0zzzzzz,
             13'b0000000000000, 3, 3, 3, 3);
    default_x = 13'b1111110111111;
    declared_x = 'x;
    declared_z = 'z;
    known = 13'b1000000000000;
    #1;
    snapshot(6, 13'b1111110111111, 13'bxxxxxxxxxxxxx, 13'bzzzzzzzzzzzzz,
             13'b1000000000000, 4, 4, 4, 4);
    $write("FOURSTATE_SENSE_INIT checks=84\n");
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
