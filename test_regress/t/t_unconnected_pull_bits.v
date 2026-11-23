// DESCRIPTION: Verilator: RTMD value/XZ address, slice and resume regressions
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps
`define stop $stop
`define checkh(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got='h%x exp='h%x\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0)
module t;
  bit phase;
  bit sample;
  pull_bits #(7) p7(phase, sample);
  pull_bits #(33) p33(phase, sample);
  pull_bits #(65) p65(phase, sample);
  pull_packed packed_bits(phase, sample);
  initial begin
    for (int n = 0; n < 4; n++) begin
      phase = (n % 2) != 0;
      #1 sample = 1;
      #1 sample = 0;
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module pull_bits #(parameter W = 1)(input bit phase, input bit sample);
  wire [W-1:0] up, down, explicit_up, explicit_down;
  bit [3:0] samples;
  // Missing inputs intentionally exercise implicit pulls.
  // verilator lint_off PINMISSING
  pull_one #(W) u(.o(up));
  pull_zero #(W) d(.o(down));
  // verilator lint_on PINMISSING
  pull_one #(W) c1(.i({W{phase}}), .o(explicit_up));
  pull_zero #(W) c0(.i({W{~phase}}), .o(explicit_down));
  always @(posedge sample) begin
    for (int b = 0; b < W; b++) begin
      `checkh(up[b], 1'b1);
      `checkh(down[b], 1'b0);
      `checkh(explicit_up[b], phase);
      `checkh(explicit_down[b], ~phase);
    end
    samples = samples + 1;
    if (samples == 4) $display("PULL_BITS width=%0d samples=4 per_bit=1 controls=1", W);
  end
endmodule

module pull_packed(input bit phase, input bit sample);
  wire [1:0][16:0] up, down, explicit_up, explicit_down;
  bit [3:0] samples;
  // verilator lint_off PINMISSING
  packed_one u(.o(up));
  packed_zero d(.o(down));
  // verilator lint_on PINMISSING
  packed_one c1(.i({34{phase}}), .o(explicit_up));
  packed_zero c0(.i({34{~phase}}), .o(explicit_down));
  always @(posedge sample) begin
    for (int a = 0; a < 2; a++) begin
      for (int b = 0; b < 17; b++) begin
        `checkh(up[a][b], 1'b1);
        `checkh(down[a][b], 1'b0);
        `checkh(explicit_up[a][b], phase);
        `checkh(explicit_down[a][b], ~phase);
      end
    end
    samples = samples + 1;
    if (samples == 4) $display("PULL_BITS width=34 samples=4 per_bit=1 controls=1");
  end
endmodule

`unconnected_drive pull1
module pull_one #(parameter W = 1)(input wire [W-1:0] i, output wire [W-1:0] o);
  assign o = i;
endmodule
module packed_one(input wire [1:0][16:0] i, output wire [1:0][16:0] o);
  assign o = i;
endmodule
`unconnected_drive pull0
module pull_zero #(parameter W = 1)(input wire [W-1:0] i, output wire [W-1:0] o);
  assign o = i;
endmodule
module packed_zero(input wire [1:0][16:0] i, output wire [1:0][16:0] o);
  assign o = i;
endmodule
`nounconnected_drive
