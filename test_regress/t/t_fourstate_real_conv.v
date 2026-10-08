// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv, expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define checkh(gotv, expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

module t;
  logic signed [7:0] signed_value;
  logic [7:0] unsigned_value;
  real value;
  integer rounded;
  longint signed wide_rounded;
  int truncated;
  logic signed [64:0] packed_rounded;
  string formatted;
  int calls;

  function automatic logic signed [7:0] selected();
    calls++;
    return signed_value;
  endfunction

  initial begin
    calls = 0;
    for (int index = -7; index <= 7; index++) begin
      signed_value = 8'(index);
      unsigned_value = 8'(index + 7);
      #1;
      value = real'(selected());
      if (value != real'(index)) `stop;
      value = real'(unsigned_value);
      if (value != real'(index + 7)) `stop;
      value = real'(index) + (index < 0 ? -0.5 : 0.5);
      rounded = value;
      truncated = $rtoi(value);
      `checkd(rounded, index < 0 ? index - 1 : index + 1);
      `checkd(truncated, index);
      `checkd(calls, index + 8);
    end
    signed_value = 8'b00x00101;
    #1;
    value = real'(selected());
    if (value != 5.0) `stop;
    signed_value = 8'b00z00101;
    #1;
    value = real'(selected());
    if (value != 5.0) `stop;
    unsigned_value = 8'bz1x00101;
    #1;
    value = real'(unsigned_value);
    if (value != 69.0) `stop;
    value = 4294967296.5;
    #1;
    wide_rounded = value;
    `checkh(wide_rounded, 64'h100000001);
    packed_rounded = value;
    `checkh(packed_rounded, 65'h100000001);
    `checkd($isunknown(packed_rounded), 0);
    rounded = 3;
    truncated = 2;
    formatted = $sformatf("%0.2f", (rounded * 100.0) / (truncated * 1.0));
    if (formatted != "150.00") `stop;
    rounded = $time / 1.0;
    `checkd(rounded, 19);
    `checkd(calls, 17);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
