// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

module t;
  `include "t_fourstate_resolve_common.vh"
  wire [5:0] done;
  triple_case #(0) p0(done[0]);
  triple_case #(1) p1(done[1]);
  triple_case #(2) p2(done[2]);
  triple_case #(3) p3(done[3]);
  triple_case #(4) p4(done[4]);
  triple_case #(5) p5(done[5]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #26;
    if (done !== '1) $fatal(1, "Triple checks did not finish");
    $display("Triple checks: %0d", p0.checks + p1.checks + p2.checks
             + p3.checks + p4.checks + p5.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module triple_case #(parameter int ORDER = 0)(output bit done = 0);
  typedef logic word_t;
  logic source_a = 1'bz, source_b = 1'bz, source_c = 1'bz;
  bit [31:0] checks = 0;
  `include "t_fourstate_resolve_common.vh"
  wire resolved_wire;
  tri resolved_tri;
  wor resolved_wor;
  wand resolved_wand;
  generate
    if (ORDER == 0) begin
      assign resolved_wire = source_a;
      assign resolved_wire = source_b;
      assign resolved_wire = source_c;
      assign resolved_tri = source_a;
      assign resolved_tri = source_b;
      assign resolved_tri = source_c;
      assign resolved_wor = source_a;
      assign resolved_wor = source_b;
      assign resolved_wor = source_c;
      assign resolved_wand = source_a;
      assign resolved_wand = source_b;
      assign resolved_wand = source_c;
    end
    if (ORDER == 1) begin
      assign resolved_wire = source_a;
      assign resolved_wire = source_c;
      assign resolved_wire = source_b;
      assign resolved_tri = source_a;
      assign resolved_tri = source_c;
      assign resolved_tri = source_b;
      assign resolved_wor = source_a;
      assign resolved_wor = source_c;
      assign resolved_wor = source_b;
      assign resolved_wand = source_a;
      assign resolved_wand = source_c;
      assign resolved_wand = source_b;
    end
    if (ORDER == 2) begin
      assign resolved_wire = source_b;
      assign resolved_wire = source_a;
      assign resolved_wire = source_c;
      assign resolved_tri = source_b;
      assign resolved_tri = source_a;
      assign resolved_tri = source_c;
      assign resolved_wor = source_b;
      assign resolved_wor = source_a;
      assign resolved_wor = source_c;
      assign resolved_wand = source_b;
      assign resolved_wand = source_a;
      assign resolved_wand = source_c;
    end
    if (ORDER == 3) begin
      assign resolved_wire = source_b;
      assign resolved_wire = source_c;
      assign resolved_wire = source_a;
      assign resolved_tri = source_b;
      assign resolved_tri = source_c;
      assign resolved_tri = source_a;
      assign resolved_wor = source_b;
      assign resolved_wor = source_c;
      assign resolved_wor = source_a;
      assign resolved_wand = source_b;
      assign resolved_wand = source_c;
      assign resolved_wand = source_a;
    end
    if (ORDER == 4) begin
      assign resolved_wire = source_c;
      assign resolved_wire = source_a;
      assign resolved_wire = source_b;
      assign resolved_tri = source_c;
      assign resolved_tri = source_a;
      assign resolved_tri = source_b;
      assign resolved_wor = source_c;
      assign resolved_wor = source_a;
      assign resolved_wor = source_b;
      assign resolved_wand = source_c;
      assign resolved_wand = source_a;
      assign resolved_wand = source_b;
    end
    if (ORDER == 5) begin
      assign resolved_wire = source_c;
      assign resolved_wire = source_b;
      assign resolved_wire = source_a;
      assign resolved_tri = source_c;
      assign resolved_tri = source_b;
      assign resolved_tri = source_a;
      assign resolved_wor = source_c;
      assign resolved_wor = source_b;
      assign resolved_wor = source_a;
      assign resolved_wand = source_c;
      assign resolved_wand = source_b;
      assign resolved_wand = source_a;
    end
  endgenerate
  initial begin
    #1;
    #0.125;
    for (int phase = 0; phase < 64; phase++) begin
      source_a = state_code(phase / 16);
      #0.125;
      source_b = state_code((phase / 4) % 4);
      #0.125;
      source_c = state_code(phase % 4);
      #0.001;
      `checkh(resolved_wire, triple_literal(0, phase));
      `checkh(resolved_tri, triple_literal(0, phase));
      `checkh(resolved_wor, triple_literal(1, phase));
      `checkh(resolved_wand, triple_literal(2, phase));
      #0.124;
    end
    done = 1;
  end
endmodule
