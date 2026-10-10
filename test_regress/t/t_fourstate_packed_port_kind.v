// DESCRIPTION: Verilator: Partial packed writes preserve variable and net defaults
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [3:0] done;
  wire [31:0] total_checks = w7.checks + w33.checks + w65.checks + w95.checks;
  packed_port_kind #(7) w7 (done[0]);
  packed_port_kind #(33) w33 (done[1]);
  packed_port_kind #(65) w65 (done[2]);
  packed_port_kind #(95) w95 (done[3]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done === 4'b1111);
    #1ps;
    $display("Packed port kind checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module packed_port_kind #(
    parameter int WIDTH = 7
) (
    output bit done = 0
);
  typedef struct packed {
    logic [WIDTH-2:0] upper;
    logic lsb;
  } word_t;
  logic [WIDTH-1:0] data = '0;
  logic [2*WIDTH-1:0] ca_variable;
  var logic [2*WIDTH-1:0] ca_explicit_variable;
  wire logic [2*WIDTH-1:0] ca_net;
  word_t [1:0][3:1] port_variable;
  var word_t [0:1][1:3] port_explicit_variable;
  wire word_t [1:0][3:1] port_net;
  bit [2*WIDTH-1:0] ca_bit;
  bit [2*WIDTH-1:0] port_bit;
  logic [WIDTH-1:0] no_writer_variable;
  wire logic [WIDTH-1:0] no_writer_net;
  /* verilator tracing_off */
  logic [WIDTH-1:0] expected_port;
  bit [WIDTH-1:0] expected_bit;
  /* verilator tracing_on */
  int unsigned checks = 0;

  assign ca_variable[WIDTH-1:0] = data;
  assign ca_explicit_variable[WIDTH-1:0] = data;
  assign ca_net[WIDTH-1:0] = data;
  assign ca_bit[WIDTH-1:0] = data;
  packed_port_driver #(WIDTH) bit_driver (
      data,
      port_bit[WIDTH-1:0]
  );
  for (genvar item = 1; item <= 3; ++item) begin : drivers
    // Rotate by a different amount so swapping packed elements is observable.
    /* verilator tracing_off */
    wire [WIDTH-1:0] source_word = {data[WIDTH-1-item:0], data[WIDTH-1:WIDTH-item]};
    /* verilator tracing_on */
    packed_port_driver #(WIDTH) variable_driver (
        source_word,
        port_variable[0][item]
    );
    packed_port_driver #(WIDTH) explicit_variable_driver (
        source_word,
        port_explicit_variable[1][item]
    );
    packed_port_driver #(WIDTH) net_driver (
        source_word,
        port_net[0][item]
    );
  end

  initial begin
    #1;
    for (int phase = 0; phase < 5; ++phase) begin
      for (int index = 0; index < WIDTH; ++index) begin
        case (phase)
          0: begin
            case (index % 4)
              0: data[index] = 1'b0;
              1: data[index] = 1'b1;
              2: data[index] = 1'bx;
              3: data[index] = 1'bz;
            endcase
          end
          1: data[index] = (index % 3 == 1);
          2: data[index] = 1'bz;
          3: data[index] = 1'bx;
          4: data[index] = (index % 3 != 1);
        endcase
        expected_bit[index] = (data[index] === 1'b1);
      end
      #1;
      `checkh(ca_variable[WIDTH-1:0], data);
      `checkh(ca_variable[2*WIDTH-1:WIDTH], {WIDTH{1'bx}});
      `checkh(ca_explicit_variable[WIDTH-1:0], data);
      `checkh(ca_explicit_variable[2*WIDTH-1:WIDTH], {WIDTH{1'bx}});
      `checkh(ca_net[WIDTH-1:0], data);
      `checkh(ca_net[2*WIDTH-1:WIDTH], {WIDTH{1'bz}});
      for (int item = 1; item <= 3; ++item) begin
        for (int index = 0; index < WIDTH; ++index) begin
          expected_port[index] = data[(index+WIDTH-item)%WIDTH];
        end
        `checkh(port_variable[0][item], expected_port);
        `checkh(port_variable[1][item], {WIDTH{1'bx}});
        `checkh(port_explicit_variable[1][item], expected_port);
        `checkh(port_explicit_variable[0][item], {WIDTH{1'bx}});
        `checkh(port_net[0][item], expected_port);
        `checkh(port_net[1][item], {WIDTH{1'bz}});
      end
      `checkh(ca_bit[WIDTH-1:0], expected_bit);
      `checkh(ca_bit[2*WIDTH-1:WIDTH], {WIDTH{1'b0}});
      `checkh(port_bit[WIDTH-1:0], expected_bit);
      `checkh(port_bit[2*WIDTH-1:WIDTH], {WIDTH{1'b0}});
      `checkh(no_writer_variable, {WIDTH{1'bx}});
      `checkh(no_writer_net, {WIDTH{1'bz}});
    end
    done = 1;
  end
endmodule

/* verilator tracing_off */
module packed_port_driver #(
    parameter int WIDTH = 7
) (
    input wire [WIDTH-1:0] source_word,
    output wire [WIDTH-1:0] result
);
  assign result = source_word;
endmodule
