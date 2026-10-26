// DESCRIPTION: Verilator: Whole packed format destinations retain value/XZ pairing
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(LABEL, GOT, EXPECTED) \
  begin \
    checks = checks + 1; \
    $display("PACKED_FORMAT_CHECK n=%0d label=%s got=%b expected=%b", checks, LABEL, (GOT), (EXPECTED)); \
    if ((GOT) !== (EXPECTED)) failures = failures + 1; \
  end
`define checks(LABEL, GOT, EXPECTED) \
  begin \
    checks = checks + 1; \
    $display("PACKED_FORMAT_CHECK n=%0d label=%s got=%s expected=%s", checks, LABEL, (GOT), (EXPECTED)); \
    if ((GOT) != (EXPECTED)) failures = failures + 1; \
  end
// verilog_format: on

`ifdef PACKED_FORMAT_MODULE
module t;
  logic [7:0] number_buffer;
  logic [31:0] ascii_buffer;
  integer checks = 0;
  integer failures = 0;
  initial begin
    $display("PACKED_FORMAT_PROFILE name=module_buffers");
    number_buffer = 'x;
    ascii_buffer = 'x;
    `checkh("number_initial", number_buffer, 8'hxx)
    `checkh("number_initial_unknown", $isunknown(number_buffer), 1'b1)
    `checkh("ascii_initial", ascii_buffer, 32'hxxxxxxxx)
    `checkh("ascii_initial_unknown", $isunknown(ascii_buffer), 1'b1)
    $sformat(number_buffer, "%0d", 7);
    `checkh("number_written", number_buffer, 8'h37)
    `checkh("number_written_unknown", $isunknown(number_buffer), 1'b0)
    $sformat(ascii_buffer, "ABCD");
    `checkh("ascii_written", ascii_buffer, 32'h41424344)
    `checkh("ascii_written_unknown", $isunknown(ascii_buffer), 1'b0)
    $display("PACKED_FORMAT_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (failures != 0) begin
      $display("%%Error: packed format mismatches=%0d", failures);
      `stop;
    end
    if (checks != 8) begin
      $display("%%Error: packed format check count=%0d expected=8", checks);
      `stop;
    end
    $display("PACKED_FORMAT_PASSED checks=8 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule

`elsif PACKED_FORMAT_TASK
module t;
  integer checks = 0;
  integer failures = 0;
  task write_local;
    logic [7:0] number_buffer;
    logic [31:0] ascii_buffer;
    begin
      number_buffer = 'x;
      ascii_buffer = 'x;
      `checkh("number_initial", number_buffer, 8'hxx)
      `checkh("number_initial_unknown", $isunknown(number_buffer), 1'b1)
      `checkh("ascii_initial", ascii_buffer, 32'hxxxxxxxx)
      `checkh("ascii_initial_unknown", $isunknown(ascii_buffer), 1'b1)
      $swrite(number_buffer, "%0d", 7);
      `checkh("number_written", number_buffer, 8'h37)
      `checkh("number_written_unknown", $isunknown(number_buffer), 1'b0)
      $swrite(ascii_buffer, "ABCD");
      `checkh("ascii_written", ascii_buffer, 32'h41424344)
      `checkh("ascii_written_unknown", $isunknown(ascii_buffer), 1'b0)
    end
  endtask
  initial begin
    $display("PACKED_FORMAT_PROFILE name=task_buffers");
    write_local;
    $display("PACKED_FORMAT_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (failures != 0) begin
      $display("%%Error: packed format mismatches=%0d", failures);
      `stop;
    end
    if (checks != 8) begin
      $display("%%Error: packed format check count=%0d expected=8", checks);
      `stop;
    end
    $display("PACKED_FORMAT_PASSED checks=8 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule

`elsif PACKED_FORMAT_SELF
module t;
  logic [7:0] ch;
  integer checks = 0;
  integer failures = 0;
  initial begin
    $display("PACKED_FORMAT_PROFILE name=module_self");
    ch = 'x;
    `checkh("self_initial", ch, 8'hxx)
    `checkh("self_initial_unknown", $isunknown(ch), 1'b1)
    $sformat(ch, "%0b", ch[0]);
    `checkh("self_written", ch, 8'h78)
    `checkh("self_written_unknown", $isunknown(ch), 1'b0)
    $display("PACKED_FORMAT_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (failures != 0) begin
      $display("%%Error: packed format mismatches=%0d", failures);
      `stop;
    end
    if (checks != 4) begin
      $display("%%Error: packed format check count=%0d expected=4", checks);
      `stop;
    end
    $display("PACKED_FORMAT_PASSED checks=4 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule

`elsif PACKED_FORMAT_TASK_SELF
module t;
  integer checks = 0;
  integer failures = 0;
  task write_local;
    logic [7:0] ch;
    begin
      ch = 'x;
      `checkh("self_initial", ch, 8'hxx)
      `checkh("self_initial_unknown", $isunknown(ch), 1'b1)
      $swrite(ch, "%0b", ch[0]);
      `checkh("self_written", ch, 8'h78)
      `checkh("self_written_unknown", $isunknown(ch), 1'b0)
    end
  endtask
  initial begin
    $display("PACKED_FORMAT_PROFILE name=task_self");
    write_local;
    $display("PACKED_FORMAT_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (failures != 0) begin
      $display("%%Error: packed format mismatches=%0d", failures);
      `stop;
    end
    if (checks != 4) begin
      $display("%%Error: packed format check count=%0d expected=4", checks);
      `stop;
    end
    $display("PACKED_FORMAT_PASSED checks=4 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule

`elsif PACKED_FORMAT_WIDTHS
module t;
  typedef logic [94:0] packed95_t;
  typedef logic [128:0] packed129_t;
  typedef logic [28:0] packed29_t;
  packed95_t buffer95;
  packed129_t buffer129;
  packed29_t buffer29;
  integer checks = 0;
  integer failures = 0;
  initial begin
    $display("PACKED_FORMAT_PROFILE name=typedef_widths");
    buffer95 = 'x;
    `checkh("w95_initial", buffer95, 95'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
    `checkh("w95_initial_unknown", $isunknown(buffer95), 1'b1)
    $sformat(buffer95, "AB");
    `checkh("w95_written", buffer95, 95'h4142)
    `checkh("w95_written_unknown", $isunknown(buffer95), 1'b0)
    buffer129 = 'x;
    `checkh("w129_initial", buffer129, 129'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
    `checkh("w129_initial_unknown", $isunknown(buffer129), 1'b1)
    $swrite(buffer129, "XYZ");
    `checkh("w129_written", buffer129, 129'h58595a)
    `checkh("w129_written_unknown", $isunknown(buffer129), 1'b0)
    buffer29 = 'x;
    `checkh("w29_initial", buffer29, 29'bxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
    `checkh("w29_initial_unknown", $isunknown(buffer29), 1'b1)
    $sformat(buffer29, "C");
    `checkh("w29_written", buffer29, 29'h43)
    `checkh("w29_written_unknown", $isunknown(buffer29), 1'b0)
    $display("PACKED_FORMAT_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (failures != 0) begin
      $display("%%Error: packed format mismatches=%0d", failures);
      `stop;
    end
    if (checks != 12) begin
      $display("%%Error: packed format check count=%0d expected=12", checks);
      `stop;
    end
    $display("PACKED_FORMAT_PASSED checks=12 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule

`elsif PACKED_FORMAT_CONTROLS
module t;
  bit [7:0] number_buffer;
  bit [31:0] ascii_buffer;
  string text_buffer;
  integer checks = 0;
  integer failures = 0;
  initial begin
    $display("PACKED_FORMAT_PROFILE name=bit_string");
    number_buffer = '0;
    ascii_buffer = '0;
    `checkh("bit_number_initial", number_buffer, 8'h00)
    `checkh("bit_ascii_initial", ascii_buffer, 32'h00000000)
    $sformat(number_buffer, "%0d", 7);
    `checkh("bit_number_written", number_buffer, 8'h37)
    `checkh("bit_number_unknown", $isunknown(number_buffer), 1'b0)
    $swrite(ascii_buffer, "ABCD");
    `checkh("bit_ascii_written", ascii_buffer, 32'h41424344)
    `checkh("bit_ascii_unknown", $isunknown(ascii_buffer), 1'b0)
    $sformat(text_buffer, "ABCD");
    `checks("string_sformat", text_buffer, "ABCD")
    $swrite(text_buffer, "%0d", 7);
    `checks("string_swrite", text_buffer, "7")
    $display("PACKED_FORMAT_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (failures != 0) begin
      $display("%%Error: packed format mismatches=%0d", failures);
      `stop;
    end
    if (checks != 8) begin
      $display("%%Error: packed format check count=%0d expected=8", checks);
      `stop;
    end
    $display("PACKED_FORMAT_PASSED checks=8 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule

`elsif PACKED_FORMAT_STRUCT
module t;
  typedef struct packed {
    logic [7:0] hi;
    logic [7:0] lo;
  } pair_t;
  pair_t pair_buffer;
  integer checks = 0;
  integer failures = 0;
  initial begin
    $display("PACKED_FORMAT_PROFILE name=packed_struct");
    pair_buffer = 'x;
    `checkh("struct_initial", pair_buffer, 16'hxxxx)
    `checkh("struct_initial_unknown", $isunknown(pair_buffer), 1'b1)
    $swrite(pair_buffer, "AB");
    `checkh("struct_written", pair_buffer, 16'h4142)
    `checkh("struct_written_unknown", $isunknown(pair_buffer), 1'b0)
    `checkh("struct_hi", pair_buffer.hi, 8'h41)
    `checkh("struct_lo", pair_buffer.lo, 8'h42)
    $display("PACKED_FORMAT_COMPLETE checks=%0d failures=%0d", checks, failures);
    if (failures != 0) begin
      $display("%%Error: packed format mismatches=%0d", failures);
      `stop;
    end
    if (checks != 6) begin
      $display("%%Error: packed format check count=%0d expected=6", checks);
      `stop;
    end
    $display("PACKED_FORMAT_PASSED checks=6 failures=0");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule

`else
module t;
  initial $fatal(1, "Select a packed format profile");
endmodule
`endif

`undef checkh
`undef checks
`undef stop
