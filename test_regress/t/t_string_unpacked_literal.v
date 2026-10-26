// DESCRIPTION: Verilator: Unpacked byte array string literal alignment
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

module t;
  typedef byte signed signed_byte_t;
  typedef byte unsigned unsigned_byte_t;
  int checks = 0;

  // IEEE string literals fill unpacked bytes from the declared left bound.
  byte signed static_desc[8:4] = "AB";
  byte unsigned static_asc[-4:-2] = "ABCDE";
  signed_byte_t equal_desc[-1:-3] = "CDE";
  byte empty_desc[6:0] = "";
  signed_byte_t nul_asc[1:5] = "\000\377A";

  byte cont_short[7:1];
  byte cont_long[-2:0];
  byte cont_empty[0:2];
  signed_byte_t cont_equal[-1:-3];
  assign cont_short = "XY";
  assign cont_long = "PQRST";
  assign cont_empty = "";
  assign cont_equal = "JKL";

  initial begin
    signed_byte_t proc_desc[4:-2];
    unsigned_byte_t proc_asc[2:6];
    logic [39:0] packed_long;
    logic [15:0] packed_short;
    packed_long = 40'("AB");
    packed_short = 16'("ABCDE");
    // Give continuous assignments a settled observation, independent of startup order.
    #1;
    `checkh(static_desc[8], 8'h41);
    `checkh(static_desc[7], 8'h42);
    `checkh(static_desc[6], 8'h00);
    `checkh(static_desc[5], 8'h00);
    `checkh(static_desc[4], 8'h00);
    `checkh(static_asc[-4], 8'h41);
    `checkh(static_asc[-3], 8'h42);
    `checkh(static_asc[-2], 8'h43);
    `checkh(equal_desc[-1], 8'h43);
    `checkh(equal_desc[-2], 8'h44);
    `checkh(equal_desc[-3], 8'h45);
    `checkh(empty_desc[6], 8'h00);
    `checkh(empty_desc[5], 8'h00);
    `checkh(empty_desc[4], 8'h00);
    `checkh(empty_desc[3], 8'h00);
    `checkh(empty_desc[2], 8'h00);
    `checkh(empty_desc[1], 8'h00);
    `checkh(empty_desc[0], 8'h00);
    `checkh(nul_asc[1], 8'h00);
    `checkh(nul_asc[2], 8'hff);
    `checkh(nul_asc[3], 8'h41);
    `checkh(nul_asc[4], 8'h00);
    `checkh(nul_asc[5], 8'h00);
    `checkh(cont_short[7], 8'h58);
    `checkh(cont_short[6], 8'h59);
    `checkh(cont_short[5], 8'h00);
    `checkh(cont_short[4], 8'h00);
    `checkh(cont_short[3], 8'h00);
    `checkh(cont_short[2], 8'h00);
    `checkh(cont_short[1], 8'h00);
    `checkh(cont_long[-2], 8'h50);
    `checkh(cont_long[-1], 8'h51);
    `checkh(cont_long[0], 8'h52);
    `checkh(cont_empty[0], 8'h00);
    `checkh(cont_empty[1], 8'h00);
    `checkh(cont_empty[2], 8'h00);
    `checkh(cont_equal[-1], 8'h4a);
    `checkh(cont_equal[-2], 8'h4b);
    `checkh(cont_equal[-3], 8'h4c);
    // Packed integral string casts retain right alignment and truncation.
    `checkh(packed_long, 40'h0000004142);
    `checkh(packed_short, 16'h4445);

    for (int phase = 0; phase < 3; ++phase) begin
      case (phase)
        0: begin proc_desc = "LM"; proc_asc = "\000\377A"; end
        1: begin proc_desc = "STUVWXYZA"; proc_asc = "pqrs"; end
        default: begin proc_desc = ""; proc_asc = "123456"; end
      endcase
      #1;
      case (phase)
        0: begin
          `checkh(proc_desc[4], 8'h4c);
          `checkh(proc_desc[3], 8'h4d);
          `checkh(proc_desc[2], 8'h00);
          `checkh(proc_desc[1], 8'h00);
          `checkh(proc_desc[0], 8'h00);
          `checkh(proc_desc[-1], 8'h00);
          `checkh(proc_desc[-2], 8'h00);
          `checkh(proc_asc[2], 8'h00);
          `checkh(proc_asc[3], 8'hff);
          `checkh(proc_asc[4], 8'h41);
          `checkh(proc_asc[5], 8'h00);
          `checkh(proc_asc[6], 8'h00);
        end
        1: begin
          `checkh(proc_desc[4], 8'h53);
          `checkh(proc_desc[3], 8'h54);
          `checkh(proc_desc[2], 8'h55);
          `checkh(proc_desc[1], 8'h56);
          `checkh(proc_desc[0], 8'h57);
          `checkh(proc_desc[-1], 8'h58);
          `checkh(proc_desc[-2], 8'h59);
          `checkh(proc_asc[2], 8'h70);
          `checkh(proc_asc[3], 8'h71);
          `checkh(proc_asc[4], 8'h72);
          `checkh(proc_asc[5], 8'h73);
          `checkh(proc_asc[6], 8'h00);
        end
        default: begin
          `checkh(proc_desc[4], 8'h00);
          `checkh(proc_desc[3], 8'h00);
          `checkh(proc_desc[2], 8'h00);
          `checkh(proc_desc[1], 8'h00);
          `checkh(proc_desc[0], 8'h00);
          `checkh(proc_desc[-1], 8'h00);
          `checkh(proc_desc[-2], 8'h00);
          `checkh(proc_asc[2], 8'h31);
          `checkh(proc_asc[3], 8'h32);
          `checkh(proc_asc[4], 8'h33);
          `checkh(proc_asc[5], 8'h34);
          `checkh(proc_asc[6], 8'h35);
        end
      endcase
    end
    `checkh(checks, 78);
    $display("Unpacked string literal checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
