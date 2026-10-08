// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
`define checkd(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  timeunit 1ps;
  timeprecision 1ps;
  integer idly = 0;
  bit [63:0] expected_delay;
  bit [31:0] delay_calls = 0;
  bit [31:0] calls_before;
  bit [31:0] two_state_calls = 0;
  logic [14:0] nba_two_state;
  time started;
  logic [14:0] value;
  logic [14:0] scheduled_value;
  logic [14:0] continuous_in = '0;
  wire [14:0] #(idly) continuous_out = continuous_in;
  logic [14:0] procedural_direct;
  logic [14:0] procedural_function;
  logic [14:0] nba_direct;
  logic [14:0] nba_function;

  function integer selected_delay();
    delay_calls = delay_calls + 1;
    return idly;
  endfunction

  function int selected_two_state_delay();
    two_state_calls++;
    return int'(expected_delay);
  endfunction

  initial begin
    #1;
    `checkh(continuous_out, 15'b0);
    for (int cycle = 0; cycle < 8; cycle++) begin
      case (cycle)
        0: begin idly = 50; expected_delay = 50; value = 15'h2355; end
        1: begin idly = 401; expected_delay = 401; value = 15'b101x001z1010010; end
        // Any unknown bit makes the entire delay zero, even with known low bits.
        2: begin idly = 32'h000000x3; expected_delay = 0; value = 'x; end
        3: begin idly = 32'h000000z3; expected_delay = 0; value = 'z; end
        4: begin idly = 'x; expected_delay = 0; value = 15'h5401; end
        5: begin idly = 'z; expected_delay = 0; value = 15'b001z110x0101101; end
        6: begin idly = 75; expected_delay = 75; value = 15'h3147; end
        7: begin idly = 339; expected_delay = 339; value = 15'h6173; end
      endcase

      // Preserve the original wire-delay case with settled, nonoverlapping inputs.
      scheduled_value = continuous_out;
      started = $time;
      continuous_in = value;
      if (expected_delay != 0) begin
        #(expected_delay - 1);
        `checkh(continuous_out, scheduled_value);
        #2;
      end else begin
        #1;
      end
      `checkd($time - started, expected_delay + 1);
      `checkh(continuous_out, value);

      procedural_direct = '0;
      started = $time;
      `checkh(procedural_direct, 15'b0);
      #(idly) procedural_direct = value;
      `checkd($time - started, expected_delay);
      `checkh(procedural_direct, value);

      procedural_function = '0;
      calls_before = delay_calls;
      started = $time;
      fork
        begin
          #(selected_delay()) procedural_function = value;
          `checkd($time - started, expected_delay);
          `checkd(delay_calls, calls_before + 1);
        end
        begin
          if (expected_delay != 0) begin
            #(expected_delay - 1);
            `checkh(procedural_function, 15'b0);
            #2;
          end else begin
            #1;
          end
          `checkh(procedural_function, value);
        end
      join

      nba_direct = '0;
      nba_function = '0;
      nba_two_state = '0;
      calls_before = delay_calls;
      started = $time;
      scheduled_value = value;
      nba_direct <= #(idly) value;
      nba_function <= #(selected_delay()) value;
      nba_two_state <= #(selected_two_state_delay()) value;
      `checkd(two_state_calls, cycle + 1);
      `checkd(delay_calls, calls_before + 1);
      `checkh(nba_direct, 15'b0);
      `checkh(nba_function, 15'b0);
      `checkh(nba_two_state, 15'b0);
      // Both delays and RHS values must be captured at the scheduling statement.
      idly = 999;
      value = ~scheduled_value;
      if (expected_delay != 0) begin
        #(expected_delay - 1);
        `checkh(nba_direct, 15'b0);
        `checkh(nba_function, 15'b0);
        `checkh(nba_two_state, 15'b0);
        #2;
      end else begin
        #1;
      end
      `checkd($time - started, expected_delay + 1);
      `checkh(nba_direct, scheduled_value);
      `checkh(nba_function, scheduled_value);
      `checkh(nba_two_state, scheduled_value);
      `checkd(two_state_calls, cycle + 1);
      `checkd(delay_calls, calls_before + 1);
    end
    `checkd(delay_calls, 32'd16);
    `checkd(two_state_calls, 32'd8);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
