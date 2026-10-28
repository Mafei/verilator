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
  int values[$];
  int result[$];
  bit [31:0] checks = 0;

  function automatic int projection(input int value, input int kind);
    case (kind)
      0: return int'(value > 3);
      1: return int'(value < 7);
      2: return int'(value > 99);
      3: return -value;
      default: return value;
    endcase
  endfunction

  task automatic check_result(input bit maximum, input int kind);
    bit member;
    bit optimal;
    int key;
    // IEEE 1800-2012 7.12.1: return an original element at the key extremum.
    // Traversal order is unspecified, so every tied original element is valid.
    `checkd(result.size(), 1);
    member = 0;
    optimal = 1;
    key = projection(result[0], kind);
    foreach (values[i]) begin
      if (result[0] == values[i]) member = 1;
      if (maximum) begin
        if (key < projection(values[i], kind)) optimal = 0;
      end else begin
        if (key > projection(values[i], kind)) optimal = 0;
      end
    end
    `checkd(member, 1'b1);
    `checkd(optimal, 1'b1);
  endtask

  initial begin
    for (int phase = 0; phase < 4; phase++) begin
      #1;
      case (phase)
        0: values = '{4, 7, 2, 5, 7, 1, 6, 3, 1};
        1: values = '{-4, -7, -2, -5, -7, -1, -6, -3, -1};
        2: values = '{8, 2, 8, 3, 2, 4};
        default: values = '{4, 4};
      endcase

      // These four calls preserve the original case122 projection expressions.
      result = values.min() with (item > 3);
      check_result(1'b0, 0);
      result = values.max() with (item < 7);
      check_result(1'b1, 1);
      // An all-false projection still has an extremum on this nonempty queue.
      result = values.min() with (item > 99);
      check_result(1'b0, 2);
      result = values.max() with (item > 99);
      check_result(1'b1, 2);

      // Negative numeric keys test projection ordering and original-value return.
      result = values.min() with (-item);
      check_result(1'b0, 3);
      result = values.max() with (-item);
      check_result(1'b1, 3);

      // Repeated equal elements do not require a first/last tie selection.
      result = values.min() with (item);
      check_result(1'b0, 4);
      result = values.max() with (item);
      check_result(1'b1, 4);
    end
    values.delete();
    result = values.min() with (item > 3);
    `checkd(result.size(), 0);
    result = values.max() with (item < 7);
    `checkd(result.size(), 0);
    result = values.min() with (item > 99);
    `checkd(result.size(), 0);
    result = values.max() with (item > 99);
    `checkd(result.size(), 0);
    $display("Queue projection checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
