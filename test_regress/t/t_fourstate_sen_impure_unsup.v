// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  logic [6:0] words [0:2];
  logic [1:0] index = 0;
  bit clk = 0;
  bit [31:0] calls = 0;
  logic [6:0] selected, whole;

  function automatic int unsigned next_index();
    calls++;
    return int'(index);
  endfunction
  function automatic logic [6:0] next_value();
    calls++;
    return words[index];
  endfunction

  // These legal forms require source side effects to be evaluated exactly once.
  always @(words[next_index()]) selected = words[index];
  always @(next_value()) whole = words[index];
`ifdef IFF_EXPLICIT_CONTROL
  always @(posedge clk) if (next_index() != 0) whole = words[index];
`else
  always @(posedge clk iff next_index() != 0) whole = words[index];
`endif
endmodule
