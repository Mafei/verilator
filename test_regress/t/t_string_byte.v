// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2022 Wilson Snyder
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d:  got='h%x exp='h%x\n", `__FILE__,`__LINE__, (gotv), (expv)); `stop; end while(0);
// verilog_format: on

module t;

  // Unpacked byte from string IEEE 1800-2023 5.9
  byte bh[3:0] = "hi2";
  byte bl[0:3] = "lo2";

  initial begin
    `checkh(bh[0], 0);
    `checkh(bh[1], "2");
    `checkh(bh[2], "i");
    `checkh(bh[3], "h");
    `checkh(bl[0], "l");
    `checkh(bl[1], "o");
    `checkh(bl[2], "2");
    `checkh(bl[3], 0);
    $write("*-* All Finished *-*\n");
    $finish;
  end

endmodule
