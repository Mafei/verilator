// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  timeunit 1ns;
  timeprecision 1ns;
  typedef bit signed [6:0] element_t;
  int int_values[$];
  int int_result[$];
  element_t bit_values[$];
  element_t bit_result[$];
  int int_minimum;
  int int_maximum;
  element_t bit_minimum;
  element_t bit_maximum;
  int projection_bias;
  bit [31:0] checks = 0;

  initial begin
    for (int phase = 0; phase < 4; phase++) begin
      #1;
      // Distinct positive elements avoid tie ordering and boolean-filter oracles.
      case (phase)
        0: begin
          int_values = '{5, 1, 9};
          bit_values = '{7'sd14, 7'sd3, 7'sd11};
          int_minimum = 1;
          int_maximum = 9;
          bit_minimum = 7'sd3;
          bit_maximum = 7'sd14;
          projection_bias = 2;
        end
        1: begin
          int_values = '{7, 12, 2};
          bit_values = '{7'sd4, 7'sd15, 7'sd9};
          int_minimum = 2;
          int_maximum = 12;
          bit_minimum = 7'sd4;
          bit_maximum = 7'sd15;
          projection_bias = 5;
        end
        2: begin
          int_values = '{13, 6, 10};
          bit_values = '{7'sd16, 7'sd12, 7'sd8};
          int_minimum = 6;
          int_maximum = 13;
          bit_minimum = 7'sd8;
          bit_maximum = 7'sd16;
          projection_bias = 3;
        end
        default: begin
          int_values = '{21, 17, 19};
          bit_values = '{7'sd23, 7'sd27, 7'sd25};
          int_minimum = 17;
          int_maximum = 21;
          bit_minimum = 7'sd23;
          bit_maximum = 7'sd27;
          projection_bias = 7;
        end
      endcase

      int_result = int_values.min() with (item);
      `checkd(int_result.size(), 1);
      `checkd(int_result[0], int_minimum);
      int_result = int_values.max() with (item);
      `checkd(int_result.size(), 1);
      `checkd(int_result[0], int_maximum);
      // The projection captures a runtime-changing, two-state external integer.
      int_result = int_values.min() with (item + projection_bias);
      `checkd(int_result.size(), 1);
      `checkd(int_result[0], int_minimum);
      int_result = int_values.max() with (item + projection_bias);
      `checkd(int_result.size(), 1);
      `checkd(int_result[0], int_maximum);

      bit_result = bit_values.min() with (item);
      `checkd(bit_result.size(), 1);
      `checkd(bit_result[0], bit_minimum);
      bit_result = bit_values.max() with (item);
      `checkd(bit_result.size(), 1);
      `checkd(bit_result[0], bit_maximum);
      bit_result = bit_values.min() with (int'(item) + projection_bias);
      `checkd(bit_result.size(), 1);
      `checkd(bit_result[0], bit_minimum);
      bit_result = bit_values.max() with (int'(item) + projection_bias);
      `checkd(bit_result.size(), 1);
      `checkd(bit_result[0], bit_maximum);
    end
    $display("Two-state queue lambda checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
