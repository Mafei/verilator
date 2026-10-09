// DESCRIPTION: Verilator: Four-state value plusargs preserve and replace both rails
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  typedef logic [32:0] word33_t;
  typedef logic signed [94:0] signed95_t;
  int checks = 0;
  int format_calls = 0;
  int code;
  int stop_at;
  int stop_enable;
  bit gate;
  logic [6:0] w7;
  logic [30:0] w31;
  word33_t w33;
  logic [64:0] w65;
  logic [94:0] w95;
  logic signed [64:0] signed65;
  signed95_t signed95;
  logic [1:7] ascending7;
  logic [36:4] offset33;

  function automatic string next_format();
    format_calls++;
    return "W7=%h";
  endfunction

  initial begin
    // These are the unchanged final-local reproducer's runtime inputs.
    stop_at = 'x;
    stop_enable = 'z;
    code = 'x;
    code = $value$plusargs("STOP_AT=%d", stop_at);
    `checkd(code, 1);
    `checkd($isunknown(code), 0);
    `checkd(stop_at, 2);
    if ($value$plusargs("STOP_ENABLE=%d", stop_enable)) begin
      `checkd(stop_enable, 0);
    end
    else begin
      `stop;
    end
    $display("INPUT stop_at=%0d stop_enable=%0d", stop_at, stop_enable);

    // No match must not modify either rail, including a mixture of X and Z.
    w7 = 7'bx1z0x1z;
    code = 'x;
    code = $value$plusargs("MISSING7=%h", w7);
    `checkd(code, 0);
    `checkd($isunknown(code), 0);
    `checkh(w7, 7'bx1z0x1z);
    w95 = 95'h123456789abcdef0xz;
    code = $value$plusargs("MISSING95=%d", w95);
    `checkd(code, 0);
    `checkh(w95, 95'h123456789abcdef0xz);
    $display("MISSING w7=%b w95=%h", w7, w95);

    // Known matches must clear every old mask bit and trim padding bits.
    w7 = 'z;
    w31 = 'x;
    w33 = 'z;
    w65 = 'x;
    w95 = 'z;
    code = $value$plusargs("W7=%h", w7);
    `checkd(code, 1);
    `checkh(w7, 7'h7f);
    code = $value$plusargs("W31=%h", w31);
    `checkd(code, 1);
    `checkh(w31, 31'h7fffffff);
    code = $value$plusargs("W33=%h", w33);
    `checkd(code, 1);
    `checkh(w33, 33'h1ffffffff);
    code = $value$plusargs("W65=%h", w65);
    `checkd(code, 1);
    `checkh(w65, 65'h1ffffffffffffffff);
    code = $value$plusargs("W95=%h", w95);
    `checkd(code, 1);
    `checkh(w95, 95'h7fffffffffffffffffffffff);
    `checkd($isunknown(w95) || $isunknown(w65) || $isunknown(w33) || $isunknown(w31) || $isunknown(w7), 0);
    ascending7 = 'x;
    offset33 = 'z;
    code = $value$plusargs("W7=%h", ascending7);
    `checkd(code, 1);
    `checkh(ascending7, 7'h7f);
    code = $value$plusargs("W33=%h", offset33);
    `checkd(code, 1);
    `checkh(offset33, 33'h1ffffffff);
    $display("KNOWN w7=%h w31=%h w33=%h w65=%h w95=%h", w7, w31, w33, w65, w95);

    // Decimal conversion extends the sign beyond 64 bits and handles 95 bits.
    signed65 = 'x;
    code = $value$plusargs("NEG65=%d", signed65);
    `checkd(code, 1);
    `checkh(signed65, -65'sd3);
    signed95 = 'z;
    code = $value$plusargs("NEG95=%d", signed95);
    `checkd(code, 1);
    `checkh(signed95, -95'sd300000000000);
    w95 = 'x;
    code = $value$plusargs("DEC95=%d", w95);
    `checkd(code, 1);
    `checkh(w95, 95'd39614081257132168796771975167);
    $display("DECIMAL signed65=%0d signed95=%0d w95=%0d", signed65, signed95, w95);
    code = $value$plusargs("NEG_CARRY=%d", signed65);
    `checkd(code, 1);
    `checkh(signed65, -65'sd4294967295);
    code = $value$plusargs("NEG_CARRY=%d", signed95);
    `checkd(code, 1);
    `checkh(signed95, -95'sd4294967295);
    $display("NEG_CARRY signed65=%0d signed95=%0d", signed65, signed95);
    code = $value$plusargs("NEG_ZERO=%d", signed65);
    `checkd(code, 1);
    `checkh(signed65, -65'sd4294967296);
    code = $value$plusargs("NEG_ZERO=%d", signed95);
    `checkd(code, 1);
    `checkh(signed95, -95'sd4294967296);
    $display("NEG_ZERO signed65=%0d signed95=%0d", signed65, signed95);

    // Based conversions preserve unknown digits and extend leading X or Z.
    code = $value$plusargs("HX33=%h", w33);
    `checkd(code, 1);
    `checkh(w33, 33'hx1);
    code = $value$plusargs("HZ65=%h", w65);
    `checkd(code, 1);
    `checkh(w65, 65'hz1);
    code = $value$plusargs("HB7=%b", w7);
    `checkd(code, 1);
    `checkh(w7, 7'b10xzz01);
    code = $value$plusargs("HO31=%o", w31);
    `checkd(code, 1);
    `checkh(w31, 31'ox1);
    code = $value$plusargs("HX95=%X", w95);
    `checkd(code, 1);
    `checkh(w95, 95'h12xzz);
    $display("BASED w7=%b w31=%b w33=%b w65=%b w95=%h", w7, w31, w33, w65, w95);
    code = $value$plusargs("DX95=%d", w95);
    `checkd(code, 1);
    `checkh(w95, {95{1'bx}});
    code = $value$plusargs("DZ95=%d", w95);
    `checkd(code, 1);
    `checkh(w95, {95{1'bz}});
    code = $value$plusargs("XX7=%x", w7);
    `checkd(code, 1);
    `checkh(w7, 7'hxz);
    $display("UNKNOWN w7=%b w95=%h", w7, w95);

    // The return is a known integer. Side effects stay in their expression.
    w7 = 'x;
    code = $value$plusargs(next_format(), w7);
    `checkd(code, 1);
    `checkh(w7, 7'h7f);
    `checkd(format_calls, 1);
    gate = $test$plusargs("GATE_NOT_PASSED");
    `checkd(gate, 0);
    w7 = 7'bx1z0x1z;
    code = int'(gate && $value$plusargs(next_format(), w7));
    `checkd(code, 0);
    `checkh(w7, 7'bx1z0x1z);
    `checkd(format_calls, 1);
    code = int'(!gate || $value$plusargs(next_format(), w7));
    `checkd(code, 1);
    `checkh(w7, 7'bx1z0x1z);
    `checkd(format_calls, 1);
    code = int'(!gate && $value$plusargs(next_format(), w7));
    `checkd(code, 1);
    `checkh(w7, 7'h7f);
    `checkd(format_calls, 2);
    w7 = 'z;
    code = int'(gate || $value$plusargs(next_format(), w7));
    `checkd(code, 1);
    `checkh(w7, 7'h7f);
    `checkd(format_calls, 3);
    w7 = 7'bx1z0x1z;
    w31 = 'z;
    code = gate ? $value$plusargs(next_format(), w7) : $value$plusargs("W31=%h", w31);
    `checkd(code, 1);
    `checkh(w7, 7'bx1z0x1z);
    `checkh(w31, 31'h7fffffff);
    `checkd(format_calls, 3);
    w31 = 'z;
    code = !gate ? $value$plusargs(next_format(), w7) : $value$plusargs("W31=%h", w31);
    `checkd(code, 1);
    `checkh(w7, 7'h7f);
    `checkh(w31, {31{1'bz}});
    `checkd(format_calls, 4);
    `checkd($isunknown(code), 0);
    $display("EXPRESSION format_calls=%0d w7=%h w31=%h", format_calls, w7, w31);
    $display("PLUSARGS checks=%0d", checks);
    $display("*-* All Finished *-*");
    $finish(0);
  end
endmodule
