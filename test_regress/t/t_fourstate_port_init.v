// DESCRIPTION: Verilator: Partial output variables keep X and implicit nets keep Z
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
  port_init_case #(7) w7 (done[0]);
  port_init_case #(33) w33 (done[1]);
  port_init_case #(65) w65 (done[2]);
  port_init_case #(95) w95 (done[3]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done === 4'b1111);
    #1ps;
    $display("Partial output initialization checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module port_init_case #(parameter int WIDTH = 7) (output bit done = 0);
  logic [WIDTH-1:0] data = '0;
  logic [2*WIDTH-1:0] default_logic;
  var logic [2*WIDTH-1:0] default_var;
  wire logic [2*WIDTH-1:0] default_wire;
  logic [2*WIDTH-1:0] explicit_logic;
  var logic [2*WIDTH-1:0] explicit_var;
  wire logic [2*WIDTH-1:0] explicit_wire;
  logic [2*WIDTH-1:0] implicit_logic;
  var logic [2*WIDTH-1:0] implicit_var;
  wire logic [2*WIDTH-1:0] implicit_wire;
  logic [2*WIDTH-1:0] net_logic;
  var logic [2*WIDTH-1:0] net_var;
  wire logic [2*WIDTH-1:0] net_wire;
  // Ascending packed ranges are deliberate controls.
  // verilator lint_off ASCRANGE
  logic [0:2*WIDTH-1] ascending_default;
  wire logic [0:2*WIDTH-1] ascending_net;
  // verilator lint_on ASCRANGE
  logic [2*WIDTH-1:0] output_unconnected_default;
  wire logic [2*WIDTH-1:0] output_unconnected_net;
  logic [2*WIDTH-1:0] inherited_typed_first;
  logic [2*WIDTH-1:0] inherited_typed_follow;
  logic [2*WIDTH-1:0] inherited_net_first;
  logic [2*WIDTH-1:0] inherited_net_follow;
  int unsigned checks = 0;

  port_init_leaf #(WIDTH) logic_targets (
      data, default_logic, explicit_logic, implicit_logic, net_logic
  );
  port_init_leaf #(WIDTH) variable_targets (
      data, default_var, explicit_var, implicit_var, net_var
  );
  port_init_leaf #(WIDTH) net_targets (
      data, default_wire, explicit_wire, implicit_wire, net_wire
  );
  port_init_ascending #(WIDTH) ascending_source (data, ascending_default, ascending_net);
  port_init_unwritten #(WIDTH) unwritten (output_unconnected_default, output_unconnected_net);
  port_init_inherited #(WIDTH) inherited_source (
      data, inherited_typed_first, inherited_typed_follow, inherited_net_first, inherited_net_follow
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
      `checkh(default_logic, {{WIDTH{1'bx}}, data});
      `checkh(default_var, {{WIDTH{1'bx}}, data});
      `checkh(default_wire, {{WIDTH{1'bx}}, data});
      `checkh(explicit_logic, {{WIDTH{1'bx}}, data});
      `checkh(explicit_var, {{WIDTH{1'bx}}, data});
      `checkh(explicit_wire, {{WIDTH{1'bx}}, data});
      `checkh(implicit_logic, {{WIDTH{1'bz}}, data});
      `checkh(implicit_var, {{WIDTH{1'bz}}, data});
      `checkh(implicit_wire, {{WIDTH{1'bz}}, data});
      `checkh(net_logic, {{WIDTH{1'bz}}, data});
      `checkh(net_var, {{WIDTH{1'bz}}, data});
      `checkh(net_wire, {{WIDTH{1'bz}}, data});
      `checkh(ascending_default, {{WIDTH{1'bx}}, data});
      `checkh(ascending_net, {{WIDTH{1'bz}}, data});
      `checkh(inherited_typed_first, {{WIDTH{1'bx}}, data});
      `checkh(inherited_typed_follow, {{WIDTH{1'bx}}, data});
      `checkh(inherited_net_first, {{WIDTH{1'bz}}, data});
      `checkh(inherited_net_follow, {{WIDTH{1'bz}}, data});
      `checkh(output_unconnected_default, {2*WIDTH{1'bx}});
      `checkh(output_unconnected_net, {2*WIDTH{1'bz}});
    end
    done = 1;
  end
endmodule

/* verilator tracing_off */
module port_init_leaf #(parameter int WIDTH = 7) (
    input wire [WIDTH-1:0] data,
    output logic [2*WIDTH-1:0] default_out,
    output var logic [2*WIDTH-1:0] explicit_out,
    output [2*WIDTH-1:0] implicit_out,
    output wire logic [2*WIDTH-1:0] net_out
);
  assign default_out[WIDTH-1:0] = data;
  assign explicit_out[WIDTH-1:0] = data;
  assign implicit_out[WIDTH-1:0] = data;
  assign net_out[WIDTH-1:0] = data;
endmodule

module port_init_ascending #(parameter int WIDTH = 7) (
    input wire [WIDTH-1:0] data,
    // verilator lint_off ASCRANGE
    output logic [0:2*WIDTH-1] default_out,
    output wire logic [0:2*WIDTH-1] net_out
    // verilator lint_on ASCRANGE
);
  assign default_out[WIDTH:2*WIDTH-1] = data;
  assign net_out[WIDTH:2*WIDTH-1] = data;
endmodule

module port_init_unwritten #(parameter int WIDTH = 7) (
    output logic [2*WIDTH-1:0] default_out,
    output wire logic [2*WIDTH-1:0] net_out
);
endmodule

module port_init_inherited #(parameter int WIDTH = 7) (
    input wire [WIDTH-1:0] data,
    output logic [2*WIDTH-1:0] typed_first, typed_follow,
    output [2*WIDTH-1:0] implicit_first, implicit_follow
);
  assign typed_first[WIDTH-1:0] = data;
  assign typed_follow[WIDTH-1:0] = data;
  assign implicit_first[WIDTH-1:0] = data;
  assign implicit_follow[WIDTH-1:0] = data;
endmodule
