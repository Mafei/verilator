// DESCRIPTION: Verilator: Partial typed output and concatenated receiving ports
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
  port_partial_case #(7) w7 (done[0]);
  port_partial_case #(33) w33 (done[1]);
  port_partial_case #(65) w65 (done[2]);
  port_partial_case #(95) w95 (done[3]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done === 4'b1111);
    #1ps;
    $display("Partial output port checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module port_partial_case #(
    parameter int WIDTH = 7,
    parameter int CUT = WIDTH / 2
) (
    output bit done = 0
);
  typedef struct packed {
    logic [WIDTH-2:0] upper;
    logic lsb;
  } word_t;
  logic [WIDTH-1:0] data = '0;
  logic [2*WIDTH-1:0] output_default;
  var logic [2*WIDTH-1:0] output_explicit_var;
  wire logic [2*WIDTH-1:0] output_net;
  wire logic [2*WIDTH-1:0] variable_to_net;
  var logic [2*WIDTH-1:0] net_to_variable;
  word_t [1:0][3:1] concat_variable;
  var word_t [0:1][1:3] concat_explicit_var;
  wire word_t [1:0][3:1] concat_net;
  logic [2*WIDTH-1:0] cross_variable;
  wire logic [2*WIDTH-1:0] cross_net;
  int unsigned checks = 0;

  partial_default #(WIDTH) default_source (data, output_default);
  partial_explicit_var #(WIDTH) explicit_source (data, output_explicit_var);
  partial_net #(WIDTH) net_source (data, output_net);
  partial_default #(WIDTH) variable_to_net_source (data, variable_to_net);
  partial_net #(WIDTH) net_to_variable_source (data, net_to_variable);
  whole_driver #(WIDTH) concat_variable_source (
      data, {concat_variable[0][3].lsb, concat_variable[0][1].upper}
  );
  whole_driver #(WIDTH) concat_explicit_source (
      data, {concat_explicit_var[1][1].lsb, concat_explicit_var[1][3].upper}
  );
  whole_driver #(WIDTH) concat_net_source (
      data, {concat_net[0][3].lsb, concat_net[0][1].upper}
  );
  whole_driver #(WIDTH) cross_variable_source (
      data, {cross_variable[WIDTH+CUT-1:WIDTH], cross_variable[WIDTH-CUT-1:0]}
  );
  whole_driver #(WIDTH) cross_net_source (
      data, {cross_net[WIDTH+CUT-1:WIDTH], cross_net[WIDTH-CUT-1:0]}
  );

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
      end
      #1;
      `checkh(output_default, {{WIDTH{1'bx}}, data});
      `checkh(output_explicit_var, {{WIDTH{1'bx}}, data});
      `checkh(output_net, {{WIDTH{1'bz}}, data});
      `checkh(variable_to_net, {{WIDTH{1'bx}}, data});
      `checkh(net_to_variable, {{WIDTH{1'bz}}, data});
      `checkh(concat_variable[1], {3*WIDTH{1'bx}});
      `checkh(concat_variable[0][3], {{(WIDTH-1){1'bx}}, data[WIDTH-1]});
      `checkh(concat_variable[0][2], {WIDTH{1'bx}});
      `checkh(concat_variable[0][1], {data[WIDTH-2:0], 1'bx});
      `checkh(concat_explicit_var[0], {3*WIDTH{1'bx}});
      `checkh(concat_explicit_var[1][1], {{(WIDTH-1){1'bx}}, data[WIDTH-1]});
      `checkh(concat_explicit_var[1][2], {WIDTH{1'bx}});
      `checkh(concat_explicit_var[1][3], {data[WIDTH-2:0], 1'bx});
      `checkh(concat_net[1], {3*WIDTH{1'bz}});
      `checkh(concat_net[0][3], {{(WIDTH-1){1'bz}}, data[WIDTH-1]});
      `checkh(concat_net[0][2], {WIDTH{1'bz}});
      `checkh(concat_net[0][1], {data[WIDTH-2:0], 1'bz});
      `checkh(cross_variable, {{(WIDTH-CUT){1'bx}}, data[WIDTH-1:WIDTH-CUT],
                             {CUT{1'bx}}, data[WIDTH-CUT-1:0]});
      `checkh(cross_net, {{(WIDTH-CUT){1'bz}}, data[WIDTH-1:WIDTH-CUT],
                        {CUT{1'bz}}, data[WIDTH-CUT-1:0]});
    end
    done = 1;
  end
endmodule

/* verilator tracing_off */
module partial_default #(parameter int WIDTH = 7) (
    input wire [WIDTH-1:0] data,
    output logic [2*WIDTH-1:0] result
);
  assign result[WIDTH-1:0] = data;
endmodule

module partial_explicit_var #(parameter int WIDTH = 7) (
    input wire [WIDTH-1:0] data,
    output var logic [2*WIDTH-1:0] result
);
  assign result[WIDTH-1:0] = data;
endmodule

module partial_net #(parameter int WIDTH = 7) (
    input wire [WIDTH-1:0] data,
    output wire logic [2*WIDTH-1:0] result
);
  assign result[WIDTH-1:0] = data;
endmodule

module whole_driver #(parameter int WIDTH = 7) (
    input wire [WIDTH-1:0] data,
    output wire [WIDTH-1:0] result
);
  assign result = data;
endmodule
