// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin ++checks; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%p exp=%p\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t (
    input clk
);
  typedef bit [31:0] key_t;
  typedef bit [64:0] wide_key_t;
  typedef struct {
    key_t member;
    key_t untouched;
  } record_t;

  class Holder;
    bit [7:0] data[key_t];
    bit [7:0] empty[key_t];
    key_t grid[2][2];
    record_t records[2];
  endclass

  Holder holder;
  int index_calls = 0;
  int receiver_calls = 0;
  int write_index_calls = 0;
  int output_calls = 0;
  int alias_index_calls = 0;
  key_t alias_calls = 0;
  int dual_calls = 0;
  int bump_calls = 0;
  int row_index;
  int column_index;
  int checks = 0;
  int cyc = 0;
  key_t selected_index[2];
  key_t grid[2][2];
  record_t records[2];
  bit [7:0] wide_data[wide_key_t];
  wide_key_t wide_index[3:2];
  bit [7:0] string_data[string];
  string string_index[2];
`ifdef FOURSTATE_REF_BOUNDS
  logic [64:0] logic_index[2];
  int logic_calls = 0;

  function automatic int logic_once(inout logic [64:0] value);
    ++logic_calls;
    if (value !== {65{1'bx}}) return 0;
    value = 65'h1_0000_0000_0000_0001;
    return 1;
  endfunction
`endif

  function automatic int index_once(input int value);
    ++index_calls;
    return value;
  endfunction

  function automatic Holder receiver_once();
    ++receiver_calls;
    return holder;
  endfunction

  function automatic int write_index_once(input int value);
    ++write_index_calls;
    return value;
  endfunction

  function automatic int output_once(output key_t value);
    ++output_calls;
    value = 321;
    return 123;
  endfunction

  function automatic int alias_index_once(input int value);
    ++alias_index_calls;
    return value;
  endfunction

  function automatic key_t alias_once(ref key_t left, ref key_t right, ref key_t calls);
    ++calls;
    left = 17;
    right = right + 1;
    return right;
  endfunction

  function automatic int dual_once(inout key_t left, inout key_t right);
    ++dual_calls;
    if (left !== 0 || right !== 0) return 0;
    left = 5;
    right = 9;
    return 1;
  endfunction

  function automatic key_t bump_once(inout key_t value);
    key_t previous;
    ++bump_calls;
    previous = value;
    value = value + 32'd1;
    return previous;
  endfunction

  initial begin
    if (!$value$plusargs("bounds_row=%d", row_index)) row_index = 1;
    if (!$value$plusargs("bounds_column=%d", column_index)) column_index = 1;
    holder = new;
    holder.data[0] = 2;
    holder.data[5] = 3;
    holder.data[9] = 4;
    wide_data[65'h0] = 1;
    wide_data[65'h1_0000_0000_0000_0000] = 2;
    wide_data[65'h1_0000_0000_0000_0001] = 3;
    string_data[""] = 1;
    string_data["middle"] = 2;
    string_data["tail"] = 3;
  end

  always @(posedge clk) begin
    int idx;
    int result;
    int expected_calls;
    idx = cyc[0] ? 4 : 1;
    expected_calls = index_calls;
    selected_index[0] = 111;
    selected_index[1] = 222;

    result = receiver_once().data.first(selected_index[index_once(idx)]);
    ++expected_calls;
    `checkh(result, 1);
    `checkh(selected_index[0], 111);
    `checkh(selected_index[1], (idx == 1) ? 0 : 222);

    result = receiver_once().data.last(selected_index[index_once(idx)]);
    ++expected_calls;
    `checkh(result, 1);
    `checkh(selected_index[0], 111);
    `checkh(selected_index[1], (idx == 1) ? 9 : 222);

    // A runtime bound prevents unrolling into distinct temporary variables.
    // Every invalid reference must read the default key again on every call.
    for (int repeat_call = 0; repeat_call < cyc + 3; ++repeat_call) begin
      if (idx == 1) selected_index[1] = 0;
      result = receiver_once().data.next(selected_index[index_once(idx)]);
      ++expected_calls;
      `checkh(result, 1);
      `checkh(selected_index[1], (idx == 1) ? 5 : 222);
      if (idx == 1) selected_index[1] = 9;
      result = receiver_once().data.prev(selected_index[index_once(idx)]);
      ++expected_calls;
      `checkh(result, (idx == 1) ? 1 : 0);
      `checkh(selected_index[1], (idx == 1) ? 5 : 222);
    end

    selected_index[1] = 222;
    result = receiver_once().empty.first(selected_index[index_once(idx)]);
    ++expected_calls;
    `checkh(result, 0);
    result = receiver_once().empty.last(selected_index[index_once(idx)]);
    ++expected_calls;
    `checkh(result, 0);
    result = receiver_once().empty.next(selected_index[index_once(idx)]);
    ++expected_calls;
    `checkh(result, 0);
    result = receiver_once().empty.prev(selected_index[index_once(idx)]);
    ++expected_calls;
    `checkh(result, 0);
    `checkh(selected_index[0], 111);
    `checkh(selected_index[1], 222);
    `checkh(index_calls, expected_calls);
    `checkh(receiver_calls, expected_calls);

    // Write-only output arguments still execute once and discard invalid writes.
    result = output_once(selected_index[write_index_once(idx)]);
    `checkh(result, 123);
    `checkh(selected_index[0], 111);
    `checkh(selected_index[1], (idx == 1) ? 321 : 222);
    `checkh(write_index_calls, cyc + 1);
    `checkh(output_calls, cyc + 1);

    // Both valid references must alias the original element, not independent copies.
    result = alias_once(selected_index[alias_index_once(1)], selected_index[alias_index_once(1)],
                        alias_calls);
    `checkh(result, 18);
    `checkh(selected_index[1], 18);
    `checkh(alias_index_calls, (cyc + 1) * 2);
    `checkh(alias_calls, cyc + 1);
    for (int repeat_call = 0; repeat_call < cyc + 3; ++repeat_call) begin
      result = dual_once(selected_index[cyc+10], selected_index[cyc+20]);
      `checkh(result, 1);
      `checkh(selected_index[0], 111);
      `checkh(selected_index[1], 18);
    end
    `checkh(dual_calls, (cyc + 1) * (cyc + 6) / 2);

    // Dynamic integer indices retain nested checked references, including members.
    grid[1][1] = 5;
    holder.grid[1][1] = 9;
    result = int'(bump_once(grid[row_index][column_index]));
    `checkh(result, 5);
    `checkh(grid[1][1], 6);
    `checkh(grid[0][0], 0);
    result = int'(bump_once(holder.grid[row_index][column_index]));
    `checkh(result, 9);
    `checkh(holder.grid[1][1], 10);
    `checkh(holder.grid[0][0], 0);
    records[1] = '{7, 9};
    holder.records[1] = '{13, 17};
    result = int'(bump_once(records[row_index].member));
    `checkh(result, 7);
    `checkh(records[1].member, 8);
    `checkh(records[1].untouched, 9);
    `checkh(records[0].member, 0);
    result = int'(bump_once(holder.records[row_index].member));
    `checkh(result, 13);
    `checkh(holder.records[1].member, 14);
    `checkh(holder.records[1].untouched, 17);
    `checkh(holder.records[0].member, 0);
    `checkh(bump_calls, (cyc + 1) * 4);

    // Non-zero descending bounds and a key wider than a machine word.
    wide_index[2] = 65'h1_0000_0000_0000_0055;
    wide_index[3] = 65'h1_0000_0000_0000_0077;
    for (int repeat_call = 0; repeat_call < cyc + 3; ++repeat_call) begin
      result = wide_data.next(wide_index[cyc+10]);
      `checkh(result, 1);
      `checkh(wide_index[2], 65'h1_0000_0000_0000_0055);
      `checkh(wide_index[3], 65'h1_0000_0000_0000_0077);
    end

    string_index[0] = "left";
    string_index[1] = "right";
    for (int repeat_call = 0; repeat_call < cyc + 3; ++repeat_call) begin
      result = string_data.next(string_index[cyc+10]);
      `checkh(result, 1);
      `checkh(string_index[0], "left");
      `checkh(string_index[1], "right");
    end

`ifdef FOURSTATE_REF_BOUNDS
    logic_index[0] = {1'bz, 32'ha5a5_5a5a, 32'h01x3_45z7};
    logic_index[1] = 65'h1_0000_0000_0000_0055;
    for (int repeat_call = 0; repeat_call < cyc + 3; ++repeat_call) begin
      result = logic_once(logic_index[cyc+10]);
      `checkh(result, 1);
      `checkh(logic_index[0], {1'bz, 32'ha5a5_5a5a, 32'h01x3_45z7});
      `checkh(logic_index[1], 65'h1_0000_0000_0000_0055);
    end
    `checkh(logic_calls, (cyc + 1) * (cyc + 6) / 2);
`endif

    ++cyc;
    if (cyc == 8) begin
      `checkh(index_calls, 152);
      `checkh(receiver_calls, 152);
      `checkh(write_index_calls, 8);
      `checkh(output_calls, 8);
      `checkh(alias_index_calls, 16);
      `checkh(alias_calls, 8);
      `checkh(dual_calls, 52);
      `checkh(bump_calls, 32);
`ifdef FOURSTATE_REF_BOUNDS
      `checkh(logic_calls, 52);
      `checkh(checks, 1162);
`else
      `checkh(checks, 997);
`endif
      $display("ASSOC_REF_BOUNDS_PASS checks=%0d calls=%0d receivers=%0d", checks, index_calls,
               receiver_calls);
      $write("*-* All Finished *-*\n");
      $finish;
    end
  end
endmodule
