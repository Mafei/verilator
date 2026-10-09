// DESCRIPTION: Verilator: Four-state packed plusargs formats convert unknown bits to zero
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  logic [23:0] bytes_value;
  logic [47:0] packed_format;
  logic [31:0] value;
  string text_value;
  int code;
  int checks = 0;
  int calls = 0;
  bit gate;

  function automatic logic [47:0] next_packed_format();
    calls++;
    return packed_format;
  endfunction

  initial begin
    // X/Z at a bit that was zero must not turn B into R.
    bytes_value = {8'h41, 8'b010x0010, 8'h43};
    text_value = bytes_value;
    `checkd(text_value.len(), 3);
    `checkh(text_value[0], 8'h41);
    `checkh(text_value[1], 8'h42);
    `checkh(text_value[2], 8'h43);
    $display("BYTES_X len=%0d c0=%0d c1=%0d c2=%0d", text_value.len(), text_value[0], text_value[1], text_value[2]);
    bytes_value = {8'h41, 8'b010z0010, 8'h43};
    text_value = bytes_value;
    `checkd(text_value.len(), 3);
    `checkh(text_value[1], 8'h42);
    $display("BYTES_Z len=%0d c0=%0d c1=%0d c2=%0d", text_value.len(), text_value[0], text_value[1], text_value[2]);
    bytes_value = {8'h41, 8'b010000x0, 8'h43};
    text_value = string'(bytes_value);
    `checkh(text_value[1], 8'h40);
    $display("CLEAR_ONE len=%0d c1=%0d", text_value.len(), text_value[1]);
    bytes_value = {8'h41, {8{1'bx}}, 8'h43};
    text_value = bytes_value;
    `checkd(text_value.len(), 2);
    `checkh(text_value[0], 8'h41);
    `checkh(text_value[1], 8'h43);
    $display("ZERO_BYTE len=%0d c0=%0d c1=%0d", text_value.len(), text_value[0], text_value[1]);

    // I has bit 1 zero. Unknown bit 1 still converts to I, not K.
    packed_format = "INT=%d";
    packed_format[41] = 1'bx;
    text_value = packed_format;
    `checkd(text_value.len(), 6);
    `checkh(text_value[0], 8'h49);
    value = 'z;
    code = $value$plusargs(packed_format, value);
    `checkd(code, 1);
    `checkh(value, 32'd1234);
    $display("FORMAT_X c0=%0d code=%0d value=%0d", text_value[0], code, value);
    value = 'x;
    code = $value$plusargs(text_value, value);
    `checkd(code, 1);
    `checkh(value, 32'd1234);
    $display("STRING_X code=%0d value=%0d", code, value);

    // I has bit 0 one. Z at bit 0 converts the first character to H.
    packed_format = "INT=%d";
    packed_format[40] = 1'bz;
    text_value = packed_format;
    `checkh(text_value[0], 8'h48);
    value = 'z;
    code = $value$plusargs(packed_format, value);
    `checkd(code, 1);
    `checkh(value, 32'd99);
    $display("FORMAT_Z c0=%0d code=%0d value=%0d", text_value[0], code, value);
    value = 'x;
    code = $value$plusargs(text_value, value);
    `checkd(code, 1);
    `checkh(value, 32'd99);
    $display("STRING_Z code=%0d value=%0d", code, value);

    // The conversion and format function remain in the selected expression.
    gate = $test$plusargs("NEVER");
    value = 'x;
    code = int'(gate && $value$plusargs(next_packed_format(), value));
    `checkd(code, 0);
    `checkd(calls, 0);
    `checkh(value, {32{1'bx}});
    $display("SKIPPED gate=%0d code=%0d calls=%0d value=%h", gate, code, calls, value);
    code = int'(!gate && $value$plusargs(next_packed_format(), value));
    `checkd(code, 1);
    `checkd(calls, 1);
    `checkh(value, 32'd99);
    $display("CALLED gate=%0d code=%0d calls=%0d value=%0d", gate, code, calls, value);
    $display("FORMAT checks=%0d", checks);
    $display("*-* All Finished *-*");
    $finish(0);
  end
endmodule
