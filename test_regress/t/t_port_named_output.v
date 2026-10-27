// DESCRIPTION: Verilator: Distinct direct named OUTPUT header aliases
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps
module named_scalar(.left(o), .right(o), d);
  output wire o;
  input wire d;
  assign o = d;
endmodule
module named_packed #(
  parameter integer W = 13
)(.left(o), .right(o), d);
  output wire [W-1:0] o;
  input wire [W-1:0] d;
  // An external alias must not replace this independent internal symbol.
  wire left;
  assign left = 1'b1;
  assign o = d;
endmodule
module t(output wire sn_left, sn_right, sp_left, sp_right,
         output wire [12:0] pn_left, pn_right, pp_left, pp_right,
         output wire [30:0] wide_left, wide_right);
  reg sn, sp;
  reg [12:0] pn, pp;
  reg [30:0] wide;
  integer checks = 0;
  integer phase;
  named_scalar scalar_named(.right(sn_right), .d(sn), .left(sn_left));
  named_scalar scalar_positional(sp_left, sp_right, sp);
  named_packed #(.W(13)) packed_named(.right(pn_right), .left(pn_left), .d(pn));
  named_packed #(.W(13)) packed_positional(pp_left, pp_right, pp);
  named_packed #(.W(31)) packed_wide(.d(wide), .right(wide_right), .left(wide_left));
  // verilog_format: off
  `define stop $stop
  `define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
  `define CHECK(gotv, expv, labelv) begin `checkh(gotv, expv); $display("NAMED_OUTPUT_CHECK n=%0d phase=%0d label=%s got=%b", checks, phase, labelv, gotv); end
  // verilog_format: on
  initial begin
    for (phase = 0; phase < 5; phase = phase + 1) begin
      case (phase)
        0: begin sn = 1'b0; sp = 1'b1; pn = 13'b0; pp = '1; wide = 31'b0; end
        1: begin sn = 1'b1; sp = 1'b0; pn = '1; pp = 13'b0; wide = '1; end
        2: begin sn = 1'bx; sp = 1'bz; pn = 'x; pp = 'z; wide = 'x; end
        3: begin sn = 1'bz; sp = 1'bx; pn = 'z; pp = 'x; wide = 'z; end
        4: begin
          sn = 1'b1; sp = 1'b0;
          pn = 13'b10xz01zx10xz0; pp = 13'bzx10xz01zx10z;
          wide = 31'b10xz01zx10xz010xz01zx10xz010xz0;
        end
      endcase
      #1;
      case (phase)
        0: begin
          `CHECK({sn_left, sn_right}, 2'b00, "scalar_named");
          `CHECK({sp_left, sp_right}, 2'b11, "scalar_positional");
          `CHECK({pn_left, pn_right}, {2{13'b0}}, "packed13_named");
          `CHECK({pp_left, pp_right}, {2{13'b1111111111111}}, "packed13_positional");
          `CHECK({wide_left, wide_right}, {2{31'b0}}, "packed31_named");
        end
        1: begin
          `CHECK({sn_left, sn_right}, 2'b11, "scalar_named");
          `CHECK({sp_left, sp_right}, 2'b00, "scalar_positional");
          `CHECK({pn_left, pn_right}, {2{13'b1111111111111}}, "packed13_named");
          `CHECK({pp_left, pp_right}, {2{13'b0}}, "packed13_positional");
          `CHECK({wide_left, wide_right}, {2{31'b1111111111111111111111111111111}}, "packed31_named");
        end
        2: begin
          `CHECK({sn_left, sn_right}, 2'bxx, "scalar_named");
          `CHECK({sp_left, sp_right}, 2'bzz, "scalar_positional");
          `CHECK({pn_left, pn_right}, {26{1'bx}}, "packed13_named");
          `CHECK({pp_left, pp_right}, {26{1'bz}}, "packed13_positional");
          `CHECK({wide_left, wide_right}, {62{1'bx}}, "packed31_named");
        end
        3: begin
          `CHECK({sn_left, sn_right}, 2'bzz, "scalar_named");
          `CHECK({sp_left, sp_right}, 2'bxx, "scalar_positional");
          `CHECK({pn_left, pn_right}, {26{1'bz}}, "packed13_named");
          `CHECK({pp_left, pp_right}, {26{1'bx}}, "packed13_positional");
          `CHECK({wide_left, wide_right}, {62{1'bz}}, "packed31_named");
        end
        4: begin
          `CHECK({sn_left, sn_right}, 2'b11, "scalar_named");
          `CHECK({sp_left, sp_right}, 2'b00, "scalar_positional");
          `CHECK({pn_left, pn_right}, {2{13'b10xz01zx10xz0}}, "packed13_named");
          `CHECK({pp_left, pp_right}, {2{13'bzx10xz01zx10z}}, "packed13_positional");
          `CHECK({wide_left, wide_right}, {2{31'b10xz01zx10xz010xz01zx10xz010xz0}}, "packed31_named");
        end
      endcase
      `CHECK(packed_named.left, 1'b1, "internal_left");
    end
    $display("NAMED_OUTPUT checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
