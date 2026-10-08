// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  timeunit 1ps;
  timeprecision 1ps;
  parameter real PDLY = 4000.0;
  real rdly = 3000.0;
  logic in = 1'b0;
  wire #2000 d_const = in;
  wire #rdly d_real = in;
  wire #PDLY d_param = in;
  logic previous = 1'b0;
  logic value;

  initial begin
    // Start with settled outputs; this test does not require an initial net value.
    #5000;
    `checkh({d_const, d_real, d_param}, 3'b000);
    for (int cycle = 0; cycle < 4; cycle++) begin
      case (cycle)
        0: value = 1'b1;
        1: value = 1'bx;
        2: value = 1'bz;
        3: value = 1'b0;
      endcase
      in = value;
      #1000;
      `checkh({d_const, d_real, d_param}, {3{previous}});
      // Sample after, rather than in the same time slot as, each delayed update.
      #1001;
      `checkh({d_const, d_real, d_param}, {value, previous, previous});
      #1000;
      `checkh({d_const, d_real, d_param}, {value, value, previous});
      #1000;
      `checkh({d_const, d_real, d_param}, {3{value}});
      previous = value;
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
