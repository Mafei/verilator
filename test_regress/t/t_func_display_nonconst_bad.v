// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module child (
    output wire [6:0] value
);
  assign value = 7'h35;
endmodule

module t;
  bit [31:0] first;

  function automatic bit [31:0] selected_bit();
    $display("selected_bit=%0d", first);
    return first;
  endfunction

`ifdef DISPLAY_PARAM
  // A runtime display argument prevents evaluation as a constant function.
  localparam int VALUE = selected_bit();
`else
  // A packed output destination requires a constant selection (IEEE 1800-2023 10.2).
  logic [20:0] word;
  child h (word[selected_bit()+:7]);
`endif
endmodule
