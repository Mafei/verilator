// DESCRIPTION: Verilator: Dynamic real decimal formats use signed rounded values
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// verilog_format: off
`define stop $stop
`define checks(LABEL, API, GOT, EXPECTED) \
  begin \
    checks = checks + 1; \
    $display("DYNAMIC_REAL_CHECK n=%0d case=%s api=%s got=%s expected=%s", checks, LABEL, API, (GOT), (EXPECTED)); \
    if ((GOT) != (EXPECTED)) failures = failures + 1; \
  end
`define checkh(LABEL, API, GOT, EXPECTED) \
  begin \
    checks = checks + 1; \
    $display("DYNAMIC_REAL_CHECK n=%0d case=%s api=%s got=%h expected=%h", checks, LABEL, API, (GOT), (EXPECTED)); \
    if ((GOT) !== (EXPECTED)) failures = failures + 1; \
  end
// verilog_format: on

module t;
  string fmt;
  string mixed_fmt;
  int wide;
  int checks = 0;
  int failures = 0;

  function automatic bit [94:0] expected_packed(input string text);
    bit [94:0] value;
    begin
      value = '0;
      for (int index = 0; index < text.len(); index = index + 1)
        value = (value << 8) | 95'(text.getc(index));
      return value;
    end
  endfunction

  task check_value(input real value, input string label_name,
                   input string minimum, input string padded);
    string expected;
    string actual;
    logic [94:0] packed_actual;
    begin
      expected = (wide != 0) ? padded : minimum;
      actual = $sformatf(fmt, value);
      `checks(label_name, "sformatf", actual, expected)
      actual = "old";
      $sformat(actual, fmt, value);
      `checks(label_name, "sformat", actual, expected)
      packed_actual = 'x;
      $sformat(packed_actual, fmt, value);
      `checkh(label_name, "packed_sformat", packed_actual, expected_packed(expected))
    end
  endtask

  initial begin
    if (!$value$plusargs("FMT=%s", fmt)) `stop;
    if (!$value$plusargs("MIX=%s", mixed_fmt)) `stop;
    if (!$value$plusargs("WIDE=%d", wide)) `stop;
    $timeformat(-9, 1, "ns", 0);
    check_value(0.0, "zero", "0", "       0");
    check_value(-0.0, "negative_zero", "0", "       0");
    check_value(1.4, "positive", "1", "       1");
    check_value(-1.4, "negative", "-1", "      -1");
    check_value(1.5, "positive_half", "2", "       2");
    check_value(-1.5, "negative_half", "-2", "      -2");
    check_value(2.5, "positive_half_three", "3", "       3");
    check_value(-2.5, "negative_half_three", "-3", "      -3");
    check_value(123.6, "positive_round", "124", "     124");
    check_value(-123.6, "negative_round", "-124", "    -124");
    check_value(2147483647.0, "int32_max", "2147483647", "2147483647");
    check_value(-2147483648.0, "int32_min", "-2147483648", "-2147483648");
    begin
      string actual;
      string expected;
      logic [94:0] packed_actual;
      expected = "1|1.4e+00|1.4|1|1.4|1.4ns|-2|a5";
      actual = $sformatf(mixed_fmt, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, -2, 8'ha5);
      `checks("mixed", "sformatf", actual, expected)
      $sformat(actual, mixed_fmt, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, -2, 8'ha5);
      `checks("mixed", "sformat", actual, expected)
      packed_actual = 'x;
      $sformat(packed_actual, mixed_fmt, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, -2, 8'ha5);
      `checkh("mixed", "packed_sformat", packed_actual, expected_packed(expected))
    end
    $display("DYNAMIC_REAL_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (checks != 39 || failures != 0) `stop;
    $display("DYNAMIC_REAL_PASS checks=39 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
