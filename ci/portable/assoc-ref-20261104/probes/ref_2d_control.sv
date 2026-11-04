// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Public control of legal dynamic two-dimensional inout arguments.
module ref_2d_control;
  class Holder;
    bit [31:0] values[2][2];
  endclass
  bit [31:0] values[2][2];
  Holder holder;
  int row_index;
  int column_index;
  bit [31:0] result;
  function automatic bit [31:0] bump(inout bit [31:0] value);
    bit [31:0] previous;
    previous = value;
    value = value + 32'd1;
    return previous;
  endfunction
  initial begin
    if (!$value$plusargs("row=%d", row_index)) row_index = 1;
    if (!$value$plusargs("column=%d", column_index)) column_index = 1;
    holder = new;
    values[1][1] = 5;
    holder.values[1][1] = 9;
    result = bump(values[row_index][column_index]);
    if (result !== 5 || values[1][1] !== 6) $fatal(1, "Two-dimensional inout differs");
    result = bump(holder.values[row_index][column_index]);
    if (result !== 9 || holder.values[1][1] !== 10) $fatal(1, "Member inout differs");
    if (values[0][0] !== 0 || holder.values[0][0] !== 0) $fatal(1, "Unselected element changed");
    $display("REF_2D_VALID_PASS calls=2");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
