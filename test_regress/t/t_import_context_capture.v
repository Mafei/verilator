// DESCRIPTION: Verilator: Parser import-context capture only.
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

package capture_pkg;
  byte entries[0:2];
  localparam int TOKEN = 7;
endpackage

byte entries[0:0];

module capture_scope #(parameter int TAG = 0);
  // verilog_format: off
`define CAP_FUNCTION before_f
`include "t_import_context_capture.vh"
`undef CAP_FUNCTION
  import capture_pkg::entries;
`define CAP_FUNCTION after_f
`include "t_import_context_capture.vh"
`undef CAP_FUNCTION
  // verilog_format: on
endmodule

import capture_pkg::TOKEN;

module t;
  capture_scope #(.TAG(0)) c0();
  capture_scope #(.TAG(1)) c1();
endmodule
