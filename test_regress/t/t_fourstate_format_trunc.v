// DESCRIPTION: Verilator: Packed formatted strings retain their suffix and clean partial bytes
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`ifdef FORMAT_TRUNC_RUNTIME
module t;
endmodule
`else
// verilog_format: off
`define stop $stop
`define checkh(LABEL, GOT, EXPECTED) \
  begin \
    checks = checks + 1; \
    $display("PACKED_TRUNC_CHECK n=%0d label=%s got=%b expected=%b", checks, LABEL, (GOT), (EXPECTED)); \
    if ((GOT) !== (EXPECTED)) failures = failures + 1; \
  end
// verilog_format: on
`ifdef FORMAT_TRUNC_FOUR_STATE
`define FORMAT_TRUNC_TYPE logic
`else
`define FORMAT_TRUNC_TYPE bit
`endif
module t;
  `FORMAT_TRUNC_TYPE [7:0] byte_buffer;
  `FORMAT_TRUNC_TYPE [14:0] half_buffer;
  `FORMAT_TRUNC_TYPE [28:0] word_buffer;
  `FORMAT_TRUNC_TYPE [31:0] dynamic_buffer;
  `FORMAT_TRUNC_TYPE [64:0] wide65_buffer;
  `FORMAT_TRUNC_TYPE [128:0] wide129_buffer;
  string format_buffer;
  integer checks = 0;
  integer failures = 0;
  initial begin
    byte_buffer = 'x;
    half_buffer = 'x;
    word_buffer = 'x;
    dynamic_buffer = 'x;
    wide65_buffer = 'x;
    wide129_buffer = 'x;
    $sformat(byte_buffer, "AB");
    `checkh("byte_long", byte_buffer, 8'h42)
    `checkh("byte_long_unknown", $isunknown(byte_buffer), 1'b0)
    $swrite(byte_buffer, "A");
    `checkh("byte_exact", byte_buffer, 8'h41)
    `checkh("byte_exact_unknown", $isunknown(byte_buffer), 1'b0)
    $sformat(half_buffer, "\377B");
    `checkh("half_partial", half_buffer, 15'h7f42)
    `checkh("half_partial_unknown", $isunknown(half_buffer), 1'b0)
    $swrite(word_buffer, "ABCD");
    `checkh("word_partial", word_buffer, 29'h01424344)
    `checkh("word_partial_unknown", $isunknown(word_buffer), 1'b0)
    $sformat(word_buffer, "");
    `checkh("word_empty", word_buffer, 29'h0)
    `checkh("word_empty_unknown", $isunknown(word_buffer), 1'b0)
    $swrite(wide65_buffer, "ZABCDEFGHI");
    `checkh("wide65_long", wide65_buffer, 65'h14243444546474849)
    `checkh("wide65_long_unknown", $isunknown(wide65_buffer), 1'b0)
    $sformat(wide129_buffer, "ZABCDEFGHIJKLMNOPQ");
    `checkh("wide129_long", wide129_buffer, 129'h142434445464748494a4b4c4d4e4f5051)
    `checkh("wide129_long_unknown", $isunknown(wide129_buffer), 1'b0)
    $swrite(wide129_buffer, "AB");
    `checkh("wide129_short", wide129_buffer, 129'h4142)
    `checkh("wide129_short_unknown", $isunknown(wide129_buffer), 1'b0)
    // Runtime prefix selection keeps this format expression from becoming a literal.
    format_buffer = $test$plusargs("other_prefix") ? "YABCD" : "ZABCD";
    $sformat(dynamic_buffer, format_buffer);
    `checkh("dynamic_long", dynamic_buffer, 32'h41424344)
    `checkh("dynamic_long_unknown", $isunknown(dynamic_buffer), 1'b0)
    $display("PACKED_TRUNC_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (checks != 18 || failures != 0) `stop;
    $display("PACKED_TRUNC_PASS checks=18 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
`undef FORMAT_TRUNC_TYPE
`undef checkh
`undef stop
`endif
