// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

module t;
  `include "t_fourstate_resolve_common.vh"
  wire [5:0] done;
  pair_width #(1) w1(done[0]);
  pair_width #(7) w7(done[1]);
  pair_width #(33) w33(done[2]);
  pair_width #(65) w65(done[3]);
  pair_width #(95) w95(done[4]);
  pair_width #(129) w129(done[5]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #8;
    if (done !== '1) $fatal(1, "Pair checks did not finish");
    $display("Pair primary checks: %0d", w1.primary_checks + w7.primary_checks + w33.primary_checks + w65.primary_checks + w95.primary_checks + w129.primary_checks);
    $display("Pair constant dynamic checks: %0d", w1.dynamic_checks + w7.dynamic_checks + w33.dynamic_checks + w65.dynamic_checks + w95.dynamic_checks + w129.dynamic_checks);
    $display("Pair constant pair checks: %0d", w1.constant_checks + w7.constant_checks + w33.constant_checks + w65.constant_checks + w95.constant_checks + w129.constant_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module pair_width #(parameter int WIDTH = 1)(output wire done);
  wire forward_done, reverse_done;
  wire [31:0] forward_checks, reverse_checks;
  pair_dynamic #(WIDTH, 0) forward(forward_done, forward_checks);
  pair_dynamic #(WIDTH, 1) reverse(reverse_done, reverse_checks);
  wire [3:0] dynamic_done;
  wire [31:0] dynamic_count [4];
  pair_constant_dynamic #(WIDTH, 0, 0) d00(dynamic_done[0], dynamic_count[0]);
  pair_constant_dynamic #(WIDTH, 1, 0) d01(dynamic_done[1], dynamic_count[1]);
  pair_constant_dynamic #(WIDTH, 0, 1) d10(dynamic_done[2], dynamic_count[2]);
  pair_constant_dynamic #(WIDTH, 1, 1) d11(dynamic_done[3], dynamic_count[3]);
  wire [31:0] constant_done;
  wire [31:0] constant_count [32];
  pair_constant #(WIDTH, 0, 0, 0) c000(constant_done[0], constant_count[0]);
  pair_constant #(WIDTH, 1, 0, 0) c001(constant_done[1], constant_count[1]);
  pair_constant #(WIDTH, 0, 0, 1) c010(constant_done[2], constant_count[2]);
  pair_constant #(WIDTH, 1, 0, 1) c011(constant_done[3], constant_count[3]);
  pair_constant #(WIDTH, 0, 0, 2) c020(constant_done[4], constant_count[4]);
  pair_constant #(WIDTH, 1, 0, 2) c021(constant_done[5], constant_count[5]);
  pair_constant #(WIDTH, 0, 0, 3) c030(constant_done[6], constant_count[6]);
  pair_constant #(WIDTH, 1, 0, 3) c031(constant_done[7], constant_count[7]);
  pair_constant #(WIDTH, 0, 1, 0) c100(constant_done[8], constant_count[8]);
  pair_constant #(WIDTH, 1, 1, 0) c101(constant_done[9], constant_count[9]);
  pair_constant #(WIDTH, 0, 1, 1) c110(constant_done[10], constant_count[10]);
  pair_constant #(WIDTH, 1, 1, 1) c111(constant_done[11], constant_count[11]);
  pair_constant #(WIDTH, 0, 1, 2) c120(constant_done[12], constant_count[12]);
  pair_constant #(WIDTH, 1, 1, 2) c121(constant_done[13], constant_count[13]);
  pair_constant #(WIDTH, 0, 1, 3) c130(constant_done[14], constant_count[14]);
  pair_constant #(WIDTH, 1, 1, 3) c131(constant_done[15], constant_count[15]);
  pair_constant #(WIDTH, 0, 2, 0) c200(constant_done[16], constant_count[16]);
  pair_constant #(WIDTH, 1, 2, 0) c201(constant_done[17], constant_count[17]);
  pair_constant #(WIDTH, 0, 2, 1) c210(constant_done[18], constant_count[18]);
  pair_constant #(WIDTH, 1, 2, 1) c211(constant_done[19], constant_count[19]);
  pair_constant #(WIDTH, 0, 2, 2) c220(constant_done[20], constant_count[20]);
  pair_constant #(WIDTH, 1, 2, 2) c221(constant_done[21], constant_count[21]);
  pair_constant #(WIDTH, 0, 2, 3) c230(constant_done[22], constant_count[22]);
  pair_constant #(WIDTH, 1, 2, 3) c231(constant_done[23], constant_count[23]);
  pair_constant #(WIDTH, 0, 3, 0) c300(constant_done[24], constant_count[24]);
  pair_constant #(WIDTH, 1, 3, 0) c301(constant_done[25], constant_count[25]);
  pair_constant #(WIDTH, 0, 3, 1) c310(constant_done[26], constant_count[26]);
  pair_constant #(WIDTH, 1, 3, 1) c311(constant_done[27], constant_count[27]);
  pair_constant #(WIDTH, 0, 3, 2) c320(constant_done[28], constant_count[28]);
  pair_constant #(WIDTH, 1, 3, 2) c321(constant_done[29], constant_count[29]);
  pair_constant #(WIDTH, 0, 3, 3) c330(constant_done[30], constant_count[30]);
  pair_constant #(WIDTH, 1, 3, 3) c331(constant_done[31], constant_count[31]);
  wire [31:0] primary_checks = forward_checks + reverse_checks;
  wire [31:0] dynamic_checks = dynamic_count[0] + dynamic_count[1]
      + dynamic_count[2] + dynamic_count[3];
  bit [31:0] constant_checks;
  always_comb begin
    constant_checks = 0;
    for (int i = 0; i < 32; i++) constant_checks += constant_count[i];
  end
  assign done = forward_done && reverse_done && (&dynamic_done) && (&constant_done);
endmodule

module pair_dynamic #(parameter int WIDTH = 1, parameter bit REVERSE = 0)
    (output bit done = 0, output bit [31:0] checks = 0);
  typedef logic [WIDTH-1:0] word_t;
  word_t source_a = 'z, source_b = 'z;
  `include "t_fourstate_resolve_common.vh"
  wire word_t resolved_wire;
  tri word_t resolved_tri;
  wor word_t resolved_wor;
  wand word_t resolved_wand;
  generate
    if (!REVERSE) begin
      assign resolved_wire = source_a;
      assign resolved_wire = source_b;
      assign resolved_tri = source_a;
      assign resolved_tri = source_b;
      assign resolved_wor = source_a;
      assign resolved_wor = source_b;
      assign resolved_wand = source_a;
      assign resolved_wand = source_b;
    end else begin
      assign resolved_wire = source_b;
      assign resolved_wire = source_a;
      assign resolved_tri = source_b;
      assign resolved_tri = source_a;
      assign resolved_wor = source_b;
      assign resolved_wor = source_a;
      assign resolved_wand = source_b;
      assign resolved_wand = source_a;
    end
  endgenerate
  initial begin
    #1;
    #0.125;
    for (int phase = 0; phase < 16; phase++) begin
      source_a = {WIDTH{state_code(phase / 4)}};
      #0.125;
      source_b = {WIDTH{state_code(phase % 4)}};
      #0.001;
      `checkh(resolved_wire, {WIDTH{pair_literal(0, phase)}});
      `checkh(resolved_tri, {WIDTH{pair_literal(0, phase)}});
      `checkh(resolved_wor, {WIDTH{pair_literal(1, phase)}});
      `checkh(resolved_wand, {WIDTH{pair_literal(2, phase)}});
      #0.124;
    end
    done = 1;
  end
endmodule

module pair_constant_dynamic #(parameter int WIDTH = 1, parameter bit REVERSE = 0,
                               parameter bit CONSTANT = 0)
    (output bit done = 0, output bit [31:0] checks = 0);
  typedef logic [WIDTH-1:0] word_t;
  word_t source = 'z;
  `include "t_fourstate_resolve_common.vh"
  wire word_t resolved_wire;
  tri word_t resolved_tri;
  wor word_t resolved_wor;
  wand word_t resolved_wand;
  generate
    if (!REVERSE) begin
      assign resolved_wire = {WIDTH{CONSTANT}};
      assign resolved_wire = source;
      assign resolved_tri = {WIDTH{CONSTANT}};
      assign resolved_tri = source;
      assign resolved_wor = {WIDTH{CONSTANT}};
      assign resolved_wor = source;
      assign resolved_wand = {WIDTH{CONSTANT}};
      assign resolved_wand = source;
    end else begin
      assign resolved_wire = source;
      assign resolved_wire = {WIDTH{CONSTANT}};
      assign resolved_tri = source;
      assign resolved_tri = {WIDTH{CONSTANT}};
      assign resolved_wor = source;
      assign resolved_wor = {WIDTH{CONSTANT}};
      assign resolved_wand = source;
      assign resolved_wand = {WIDTH{CONSTANT}};
    end
  endgenerate
  initial begin
    #1;
    #0.125;
    for (int phase = 0; phase < 4; phase++) begin
      source = {WIDTH{state_code(phase)}};
      #0.001;
      `checkh(resolved_wire, {WIDTH{pair_literal(0, int'(CONSTANT) * 4 + phase)}});
      `checkh(resolved_tri, {WIDTH{pair_literal(0, int'(CONSTANT) * 4 + phase)}});
      `checkh(resolved_wor, {WIDTH{pair_literal(1, int'(CONSTANT) * 4 + phase)}});
      `checkh(resolved_wand, {WIDTH{pair_literal(2, int'(CONSTANT) * 4 + phase)}});
      #0.249;
    end
    done = 1;
  end
endmodule

module pair_constant #(parameter int WIDTH = 1, parameter bit REVERSE = 0,
                       parameter int A = 0, parameter int B = 0)
    (output bit done = 0, output bit [31:0] checks = 0);
  typedef logic [WIDTH-1:0] word_t;
  `include "t_fourstate_resolve_common.vh"
  wire word_t resolved_wire;
  tri word_t resolved_tri;
  wor word_t resolved_wor;
  wand word_t resolved_wand;
  generate
    if (!REVERSE) begin
      assign resolved_wire = {WIDTH{state_code(A)}};
      assign resolved_wire = {WIDTH{state_code(B)}};
      assign resolved_tri = {WIDTH{state_code(A)}};
      assign resolved_tri = {WIDTH{state_code(B)}};
      assign resolved_wor = {WIDTH{state_code(A)}};
      assign resolved_wor = {WIDTH{state_code(B)}};
      assign resolved_wand = {WIDTH{state_code(A)}};
      assign resolved_wand = {WIDTH{state_code(B)}};
    end else begin
      assign resolved_wire = {WIDTH{state_code(B)}};
      assign resolved_wire = {WIDTH{state_code(A)}};
      assign resolved_tri = {WIDTH{state_code(B)}};
      assign resolved_tri = {WIDTH{state_code(A)}};
      assign resolved_wor = {WIDTH{state_code(B)}};
      assign resolved_wor = {WIDTH{state_code(A)}};
      assign resolved_wand = {WIDTH{state_code(B)}};
      assign resolved_wand = {WIDTH{state_code(A)}};
    end
  endgenerate
  initial begin
    #1;
    `checkh(resolved_wire, {WIDTH{pair_literal(0, A * 4 + B)}});
    `checkh(resolved_tri, {WIDTH{pair_literal(0, A * 4 + B)}});
    `checkh(resolved_wor, {WIDTH{pair_literal(1, A * 4 + B)}});
    `checkh(resolved_wand, {WIDTH{pair_literal(2, A * 4 + B)}});
    done = 1;
  end
endmodule
