// DESCRIPTION: Verilator: One direct named OUTPUT alias per internal wire
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps
module unique_output #(
  parameter integer W = 33
)(.result(q), d);
  output wire [W+2:3] q;
  input wire [W+2:3] d;
  assign q = d;
endmodule
module t(output wire [35:3] q33, result, output wire [67:3] q65);
  reg [35:3] d33;
  reg [67:3] d65;
  reg [35:3] d;
  integer checks = 0;
  integer phase;
  unique_output named33(.d(d33), .result(q33));
  unique_output #(.W(65)) positional65(q65, d65);
  unique_output star33(.*);
  // verilog_format: off
  `define stop $stop
  `define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
  `define CHECK(gotv, expv, labelv) begin `checkh(gotv, expv); $display("NAMED_UNIQUE_CHECK n=%0d phase=%0d label=%s got=%b", checks, phase, labelv, gotv); end
  // verilog_format: on
  initial begin
    for (phase = 0; phase < 5; phase = phase + 1) begin
      case (phase)
        0: begin d33 = 33'b0; d65 = '1; d = '1; end
        1: begin d33 = '1; d65 = 65'b0; d = 33'b0; end
        2: begin d33 = 'x; d65 = 'z; d = 'z; end
        3: begin d33 = 'z; d65 = 'x; d = 'x; end
        4: begin
          d33 = 33'b10xz01zx10xz01zx10xz01zx10xz01zx0;
          d65 = 65'bzx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz101;
          d = 33'b01zx10xz01zx10xz01zx10xz01zx10xz1;
        end
      endcase
      #1;
      case (phase)
        0: begin
          `CHECK(q33, 33'b0, "named33");
          `CHECK(q65, 65'b11111111111111111111111111111111111111111111111111111111111111111, "positional65");
          `CHECK(result, 33'b111111111111111111111111111111111, "star33");
        end
        1: begin
          `CHECK(q33, 33'b111111111111111111111111111111111, "named33");
          `CHECK(q65, 65'b0, "positional65");
          `CHECK(result, 33'b0, "star33");
        end
        2: begin
          `CHECK(q33, {33{1'bx}}, "named33");
          `CHECK(q65, {65{1'bz}}, "positional65");
          `CHECK(result, {33{1'bz}}, "star33");
        end
        3: begin
          `CHECK(q33, {33{1'bz}}, "named33");
          `CHECK(q65, {65{1'bx}}, "positional65");
          `CHECK(result, {33{1'bx}}, "star33");
        end
        4: begin
          `CHECK(q33, 33'b10xz01zx10xz01zx10xz01zx10xz01zx0, "named33");
          `CHECK(q65, 65'bzx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz101, "positional65");
          `CHECK(result, 33'b01zx10xz01zx10xz01zx10xz01zx10xz1, "star33");
          `CHECK(q33[35], 1'b1, "named33_msb35");
          `CHECK(q33[3], 1'b0, "named33_lsb3");
          `CHECK(q65[67], 1'bz, "positional65_msb67");
          `CHECK(q65[3], 1'b1, "positional65_lsb3");
        end
      endcase
    end
    $display("NAMED_UNIQUE checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
