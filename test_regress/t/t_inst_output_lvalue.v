// DESCRIPTION: Verilator: Writable output port connection forms
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

typedef struct packed {
  logic [2:0] tag;
  logic [3:0] data;
} packet_t;

module source (input logic [6:0] value, output wire [6:0] data);
  assign data = value;
endmodule

module packet_source (input logic [6:0] value, output wire packet_t data);
  assign data = packet_t'(value);
endmodule

module hierarchy_sink;
  wire [6:0] data;
endmodule

module t (input logic clk);
  int unsigned checks = 0;
  logic [6:0] value;
  wire [6:0] simple;
  wire [6:0] concat_value;
  wire [6:0] stream_value;
  wire [14:0] selected;
  wire [2:0] tag;
  wire [2:0] typed_tag;
  wire [3:0] data;
  wire [3:0] typed_data;
  localparam int WRITE_SINK = 1;
  hierarchy_sink sinks[0:1] ();

  source simple_source (value + 7'h1, simple);
  source concat_source (value, {concat_value[6:4], concat_value[3:0]});
  source stream_source (value, {>>{stream_value}});
  source select_source (value, selected[(3+4)+:7]);
  packet_source positional_source (value, '{tag, data});
  packet_source typed_source (value, packet_t'{typed_tag, typed_data});
  source hierarchy_source (value, sinks[WRITE_SINK].data);

  initial begin
    for (int i = 0; i < 8; ++i) begin
      @(negedge clk);
      value = 7'(i*13+5);
      #1;
      `checkh(simple, 7'(value+7'h1));
      `checkh(concat_value, value);
      `checkh(stream_value, value);
      `checkh(selected[13:7], value);
      `checkh({tag, data}, value);
      `checkh({typed_tag, typed_data}, value);
      `checkh(sinks[WRITE_SINK].data, value);
    end
    `checkh(checks, 57);
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
