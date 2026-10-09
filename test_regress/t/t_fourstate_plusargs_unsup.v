// DESCRIPTION: Verilator: Legal selected plusargs outputs outside the whole-variable boundary
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
`ifdef PLUSARGS_LEGACY_BITS
  // This is inherited two-state storage with a four-state index expression.
  // Icarus 12 rejects this selected output; the control has no reference gold.
  bit [6:0] bits_array [0:1];
  logic [31:0] index_value = 0;
  int code;
  int checks = 0;
  initial begin
    bits_array[0] = 7'h11;
    bits_array[1] = 7'h22;
    code = $value$plusargs("W7=%h", bits_array[index_value++]);
    `checkd(code, 32'd1);
    `checkd(index_value, 32'd1);
    `checkd(bits_array[0], 7'h7f);
    `checkd(bits_array[1], 7'h22);
    $display("LEGACY_BITS checks=%0d", checks);
    $display("*-* All Finished *-*");
    $finish(0);
  end
`else
  logic [32:0] packed_value;
  logic [6:0] unpacked_value [0:1];
  int index_value = 0;
  int code;
  initial begin
`ifdef PLUSARGS_UNSUP_SLICE
    code = $value$plusargs("SLICE=%h", packed_value[6:0]);
`else
    code = $value$plusargs("ELEMENT=%d", unpacked_value[index_value++]);
`endif
  end
`endif
endmodule
