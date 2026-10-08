// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  integer calls = 0;
  logic [6:0] source;
  logic [6:0] target;
  wire [6:0] #(delay_value()) delayed = source;

  wire [6:0] #(two_state_delay()) delayed_two_state = source;

  wire [6:0] #(two_state_delay()) separate;
  assign separate = source;

  wire [6:0] #(2, two_state_delay()) falling = source;
  wire [6:0] #(2, delay_value()) separate_falling;
  assign separate_falling = source;

  function int two_state_delay();
    calls++;
    return 3;
  endfunction

  function integer delay_value();
    calls++;
    return 2;
  endfunction

  initial begin
    source = 7'b001xz01;
    target = #(2) source;
  end
endmodule
