// DESCRIPTION: Verilator: Partially overlapping packed slices retain valid bits
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

module slice_bounds_case #(
    parameter int WIDTH = 7,
    parameter int LOW = 0,
    parameter int SLICE = 4
) (
    output bit done
);
  localparam int HIGH = LOW + WIDTH - 1;
  int checks = 0;
  int calls = 0;
  bit phase = 0;
  logic [HIGH:LOW] descending;
  logic [LOW:HIGH] ascending;
  logic signed [31:0] requested = 0;
  bit [31:0] unsigned_requested = 0;
  logic [SLICE-1:0] actual, expected;

  // The oracle uses literal four-state symbols and physical bit coordinates.
  function automatic logic expected_bit(input int coordinate, input bit flip);
    if (coordinate < 0 || coordinate >= WIDTH) return 1'bx;
    case (coordinate % 7)
      0, 2, 6: return ~flip;
      1, 5: return flip;
      3: return 1'bx;
      4: return 1'bz;
    endcase
  endfunction
  function automatic logic [SLICE-1:0] expected_slice(input int coordinate, input bit flip);
    for (int bit_index = 0; bit_index < SLICE; ++bit_index)
    expected_slice[bit_index] = expected_bit(coordinate + bit_index, flip);
  endfunction
  function automatic bit [31:0] called_index(input bit [31:0] index);
    calls++;
    return index;
  endfunction

  initial begin
    done = 0;
    for (int phase_index = 0; phase_index < 2; ++phase_index) begin
      phase = 1'(phase_index);
      for (int coordinate = 0; coordinate < WIDTH; ++coordinate) begin
        descending[LOW+coordinate] = expected_bit(coordinate, phase);
        ascending[HIGH-coordinate] = expected_bit(coordinate, phase);
      end
      #100;
      for (int coordinate = -SLICE - 2; coordinate <= WIDTH + SLICE + 2; ++coordinate) begin
        expected = expected_slice(coordinate, phase);
        requested = LOW + coordinate;
        actual = descending[requested+:SLICE];
        `checkh(actual, expected);
        requested = LOW + coordinate + SLICE - 1;
        actual = descending[requested-:SLICE];
        `checkh(actual, expected);
        requested = HIGH - coordinate - SLICE + 1;
        actual = ascending[requested+:SLICE];
        `checkh(actual, expected);
        requested = HIGH - coordinate;
        actual = ascending[requested-:SLICE];
        `checkh(actual, expected);
        #10;
      end
      // Unsigned zero can overlap a nonzero declaration; it is not a wrapped negative.
      unsigned_requested = 0;
      actual = descending[unsigned_requested+:SLICE];
      `checkh(actual, expected_slice(-LOW, phase));
      actual = ascending[unsigned_requested+:SLICE];
      `checkh(actual, expected_slice(HIGH - SLICE + 1, phase));
      requested = 'x;
      actual = descending[requested+:SLICE];
      `checkh(actual, {SLICE{1'bx}});
      requested = 'z;
      actual = ascending[requested-:SLICE];
      `checkh(actual, {SLICE{1'bx}});
      unsigned_requested = 32'(LOW + 1);
      calls = 0;
      actual = descending[called_index(unsigned_requested)+:SLICE];
      `checkh(calls, 1);
      `checkh(actual, expected_slice(1, phase));
    end
    $display("CHECKS %m %0d", checks);
    done = 1;
  end
endmodule

module t;
  wire [4:0] done;
  slice_bounds_case #(
      .WIDTH(7),
      .LOW(0),
      .SLICE(4)
  ) c7 (
      done[0]
  );
  slice_bounds_case #(
      .WIDTH(31),
      .LOW(-2),
      .SLICE(9)
  ) c31 (
      done[1]
  );
  slice_bounds_case #(
      .WIDTH(33),
      .LOW(8),
      .SLICE(16)
  ) c33 (
      done[2]
  );
  slice_bounds_case #(
      .WIDTH(65),
      .LOW(5),
      .SLICE(9)
  ) c65 (
      done[3]
  );
  slice_bounds_case #(
      .WIDTH(95),
      .LOW(9),
      .SLICE(4)
  ) c95 (
      done[4]
  );
  initial begin
    wait (&done);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
