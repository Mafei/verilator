// DESCRIPTION: Verilator: Output connections require lvalue expressions
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

typedef struct packed {logic [2:0] tag; logic [3:0] data;} output_packet_t;

interface output_if (output wire [6:0] data);
  assign data = 7'h35;
endinterface

module output_module (output wire [6:0] data);
  assign data = 7'h35;
endmodule

module output_packet (output wire output_packet_t data);
  assign data = 7'h35;
endmodule

module output_array (output wire [6:0] data[2]);
  assign data = '{7'h13, 7'h29};
endmodule

module output_wide (output wire [13:0] data);
  assign data = 14'h3535;
endmodule

module t;
  logic [6:0] a = 7'h13;
  logic [6:0] b = 7'h29;
  logic choose = 1;
  function automatic logic [6:0] value();
    return a;
  endfunction
  // Each value expression is illegal even when all its operands are writable.
  output_module arithmetic (a + b);
  output_if interface_arithmetic (a + b);
  output_module unary (~a);
  output_module conditional_value (choose ? a : b);
  output_module function_value (value());
  output_module cast_value (7'(a));
  output_module concat_value ({a[6:4], b[3:0] + 4'h1});
  output_packet keyed_value ('{tag:a[6:4], data:b[3:0]});
  output_array replicated_value ('{2{a}});
  output_wide packed_replication ({2{a}});
endmodule
