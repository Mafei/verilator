// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [4:0] done;
  wire [31:0] total_checks = w1.checks + w7.checks + w33.checks + w65.checks + w95.checks;
  undriven_width #(1) w1(done[0]);
  undriven_width #(7) w7(done[1]);
  undriven_width #(33) w33(done[2]);
  undriven_width #(65) w65(done[3]);
  undriven_width #(95) w95(done[4]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done === '1);
    #1;
    $display("Floating inout checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

interface undriven_bus #(parameter int WIDTH = 1);
  wire [WIDTH-1:0] net_wire;
  tri [WIDTH-1:0] net_tri;
  wand [WIDTH-1:0] net_wand;
  wor [WIDTH-1:0] net_wor;
  triand [WIDTH-1:0] net_triand;
  trior [WIDTH-1:0] net_trior;
endinterface

module undriven_interface(undriven_bus bus);
  empty_inout #($bits(bus.net_wire)) p0(bus.net_wire);
  empty_inout #($bits(bus.net_tri)) p1(bus.net_tri);
  empty_inout #($bits(bus.net_wand)) p2(bus.net_wand);
  empty_inout #($bits(bus.net_wor)) p3(bus.net_wor);
  empty_inout #($bits(bus.net_triand)) p4(bus.net_triand);
  empty_inout #($bits(bus.net_trior)) p5(bus.net_trior);
endmodule

module undriven_width #(parameter int WIDTH = 1)(output bit done = 0);
  wire [WIDTH-1:0] bare_wire;
  tri [WIDTH-1:0] bare_tri;
  wand [WIDTH-1:0] bare_wand;
  wor [WIDTH-1:0] bare_wor;
  triand [WIDTH-1:0] bare_triand;
  trior [WIDTH-1:0] bare_trior;
  wire [WIDTH-1:0] connected_wire;
  tri [WIDTH-1:0] connected_tri;
  wand [WIDTH-1:0] connected_wand;
  wor [WIDTH-1:0] connected_wor;
  triand [WIDTH-1:0] connected_triand;
  trior [WIDTH-1:0] connected_trior;
  tri0 [WIDTH-1:0] pulled_down;
  tri1 [WIDTH-1:0] pulled_up;
  wire [WIDTH-1:0] child_down;
  wire [WIDTH-1:0] child_up;
  undriven_bus #(WIDTH) bus();
  undriven_interface bridge(bus);
  wire [WIDTH-1:0] interface_wire = bus.net_wire;
  wire [WIDTH-1:0] interface_tri = bus.net_tri;
  wire [WIDTH-1:0] interface_wand = bus.net_wand;
  wire [WIDTH-1:0] interface_wor = bus.net_wor;
  wire [WIDTH-1:0] interface_triand = bus.net_triand;
  wire [WIDTH-1:0] interface_trior = bus.net_trior;
  empty_inout #(WIDTH) p0(connected_wire);
  empty_inout #(WIDTH) p1(connected_tri);
  empty_inout #(WIDTH) p2(connected_wand);
  empty_inout #(WIDTH) p3(connected_wor);
  empty_inout #(WIDTH) p4(connected_triand);
  empty_inout #(WIDTH) p5(connected_trior);
  default_pull_outputs #(WIDTH) pulls(child_down, child_up);
`ifdef TWOSTATE_BOUNDARY
  tri0 [WIDTH-1:0] connected_down;
  tri1 [WIDTH-1:0] connected_up;
  wire [WIDTH-1:0] explicit_down;
  wire [WIDTH-1:0] explicit_up;
  pulldown (explicit_down);
  pullup (explicit_up);
  empty_inout #(WIDTH) pd0(connected_down);
  empty_inout #(WIDTH) pd1(connected_up);
  empty_inout #(WIDTH) pe0(explicit_down);
  empty_inout #(WIDTH) pe1(explicit_up);
`endif
  int checks = 0;
  initial begin
    repeat (3) begin
      #1;
`ifndef TWOSTATE_BOUNDARY
      `checkh(bare_wire, {WIDTH{1'bz}});
      `checkh(bare_tri, {WIDTH{1'bz}});
      `checkh(bare_wand, {WIDTH{1'bz}});
      `checkh(bare_wor, {WIDTH{1'bz}});
      `checkh(bare_triand, {WIDTH{1'bz}});
      `checkh(bare_trior, {WIDTH{1'bz}});
      `checkh(connected_wire, {WIDTH{1'bz}});
      `checkh(connected_tri, {WIDTH{1'bz}});
      `checkh(connected_wand, {WIDTH{1'bz}});
      `checkh(connected_wor, {WIDTH{1'bz}});
      `checkh(connected_triand, {WIDTH{1'bz}});
      `checkh(connected_trior, {WIDTH{1'bz}});
      `checkh(interface_wire, {WIDTH{1'bz}});
      `checkh(interface_tri, {WIDTH{1'bz}});
      `checkh(interface_wand, {WIDTH{1'bz}});
      `checkh(interface_wor, {WIDTH{1'bz}});
      `checkh(interface_triand, {WIDTH{1'bz}});
      `checkh(interface_trior, {WIDTH{1'bz}});
`else
      `checkh(connected_down, {WIDTH{1'b0}});
      `checkh(connected_up, {WIDTH{1'b1}});
      `checkh(explicit_down, {WIDTH{1'b0}});
      `checkh(explicit_up, {WIDTH{1'b1}});
`endif
      `checkh(pulled_down, {WIDTH{1'b0}});
      `checkh(pulled_up, {WIDTH{1'b1}});
      `checkh(child_down, {WIDTH{1'b0}});
      `checkh(child_up, {WIDTH{1'b1}});
    end
    done = 1;
  end
endmodule

module empty_inout #(parameter int WIDTH = 1)(inout wire [WIDTH-1:0] value);
endmodule

module default_pull_outputs #(parameter int WIDTH = 1)
    (output tri0 [WIDTH-1:0] down, output tri1 [WIDTH-1:0] up);
endmodule
