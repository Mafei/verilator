// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checks(gotv, expv) do if ((gotv) != (expv)) begin $write("%%Error: %s:%0d: got=%s expected=%s\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0)
`define checkhex(gotv, expv, refv) do if ((gotv) != (expv) && (gotv) != (refv)) begin $write("%%Error: %s:%0d: got=%s expected=%s or %s\n", `__FILE__, `__LINE__, (gotv), (expv), (refv)); `stop; end while (0)
// verilog_format: on

module t;
  logic p;
  integer unsigned q;
  integer o;
  logic [64:0] wide65;
  logic [94:0] wide95;
  string formatted;
  logic format_bit;

  function integer foo(integer a, integer b);
    return a + b;
  endfunction

  initial begin
    static logic v = 'x;
    $write("%h\n", v);
    v = 'z;
    $write("%h\n", v);
    v = 0;
    $write("%h\n", v);
    v = 1;
    $write("%h\n", v);
    $write("%h\n", foo(1, 2));

    $write("%h\n%h\n", p, q);
    p = 'z;
    q = 'z;
    $write("%h\n%h\n", p, q);
    p = 1;
    q = 1;
    $write("%h\n%h\n", p, q);
    p = 0;
    q = 0;
    $write("%h\n%h\n", p, q);
    q = 32'b01x;
    $write("%h\n", q);
    q = 32'b01z;
    $write("%h\n", q);
    q = 32'b01xz;
    $write("%h\n", q);
    q = 32'b0101;
    $write("%h\n", q);
    q = 32'bxz;
    $write("%h\n", q);
    q = 32'bzx;
    $write("%h\n", q);

    $write("%h\n", o);
    o = 'z;
    $write("%h\n", o);
    o = 1;
    $write("%h\n", o);
    o = 0;
    $write("%h\n", o);
    o = 32'b01x;
    $write("%h\n", o);
    o = 32'b01z;
    $write("%h\n", o);
    o = 32'b01xz;
    $write("%h\n", o);
    o = 32'b0101;
    $write("%h\n", o);
    o = 32'bxz;
    $write("%h\n", o);
    o = 32'bzx;
    $write("%h\n", o);
    o = 32'h908faczx;
    $write("%h\n", o);

    // Exercise both wide arguments of the four-state formatting ABI.
    // Reference simulators differ in case for partial all-X/Z hex digits.
    for (int cycle = 0; cycle < 4; cycle++) begin
      case (cycle)
        0: format_bit = 1'b0;
        1: format_bit = 1'b1;
        2: format_bit = 1'bx;
        3: format_bit = 1'bz;
      endcase
      #1;
      formatted = $sformatf("%h", {7{format_bit}});
      case (cycle)
        0: `checks(formatted, "00");
        1: `checks(formatted, "7f");
        2: `checkhex(formatted, "xx", "Xx");
        3: `checkhex(formatted, "zz", "Zz");
      endcase
      formatted = $sformatf("%h", {33{format_bit}});
      case (cycle)
        0: `checks(formatted, "000000000");
        1: `checks(formatted, "1ffffffff");
        2: `checkhex(formatted, "xxxxxxxxx", "Xxxxxxxxx");
        3: `checkhex(formatted, "zzzzzzzzz", "Zzzzzzzzz");
      endcase
      formatted = $sformatf("%0d", {7{format_bit}});
      case (cycle)
        0: `checks(formatted, "0");
        1: `checks(formatted, "127");
        2: `checks(formatted, "x");
        3: `checks(formatted, "z");
      endcase
      formatted = $sformatf("%0d", {33{format_bit}});
      case (cycle)
        0: `checks(formatted, "0");
        1: `checks(formatted, "8589934591");
        2: `checks(formatted, "x");
        3: `checks(formatted, "z");
      endcase
      formatted = $sformatf("%0d", {65{format_bit}});
      case (cycle)
        0: `checks(formatted, "0");
        1: `checks(formatted, "36893488147419103231");
        2: `checks(formatted, "x");
        3: `checks(formatted, "z");
      endcase
      formatted = $sformatf("%0d", {95{format_bit}});
      case (cycle)
        0: `checks(formatted, "0");
        1: `checks(formatted, "39614081257132168796771975167");
        2: `checks(formatted, "x");
        3: `checks(formatted, "z");
      endcase
      formatted = $sformatf("%0d", $signed({7{format_bit}}));
      case (cycle)
        0: `checks(formatted, "0");
        1: `checks(formatted, "-1");
        2: `checks(formatted, "x");
        3: `checks(formatted, "z");
      endcase
      formatted = $sformatf("%0d", $signed({95{format_bit}}));
      case (cycle)
        0: `checks(formatted, "0");
        1: `checks(formatted, "-1");
        2: `checks(formatted, "x");
        3: `checks(formatted, "z");
      endcase
      wide65 = 65'h0xz0123456789abcd;
      wide95 = 'x;
      #1;
      formatted = $sformatf("%h", wide65);
      `checks(formatted, "0xz0123456789abcd");
      formatted = $sformatf("%h", wide95);
      `checkhex(formatted, "xxxxxxxxxxxxxxxxxxxxxxxx", "Xxxxxxxxxxxxxxxxxxxxxxxx");
      wide65 = 'z;
      wide95 = '1;
      #1;
      formatted = $sformatf("%h", wide65);
      `checkhex(formatted, "zzzzzzzzzzzzzzzzz", "Zzzzzzzzzzzzzzzzz");
      formatted = $sformatf("%h", wide95);
      `checks(formatted, "7fffffffffffffffffffffff");
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
