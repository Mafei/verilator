// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin \
  ++checks; \
  if ((gotv) !== (expv)) begin \
    $write("%%Error: %s:%0d: check=%0d got=%p exp=%p\n", `__FILE__, `__LINE__, checks, (gotv), (expv)); \
    `stop; \
  end \
end while (0);
// verilog_format: on

module t;
  typedef bit [30:0] word_t;
  word_t words[2];
  word_t result;
  word_t left_value;
  word_t other_value;
  int checks = 0;
  int calls = 0;
  int cycles;
  int selected_case;
  int index_value;
  int other_index;
  int expected_checks;
  int expected_calls;

  // Each selected element is a ref, forcing the non-inlined function path.
  function automatic word_t read_left(ref word_t left, ref word_t right);
    left = 17;
    right = right + 1;
    return left;
  endfunction

  // The first assignment must survive a read through a possibly aliased formal.
  function automatic word_t middle_read(ref word_t left, const ref word_t right);
    // verilator no_inline_task
    word_t seen;
    left = 17;
    seen = right;
    left = 29;
    return seen;
  endfunction

  function automatic word_t reverse_write(ref word_t left, ref word_t right);
    right = 11;
    left = left + 2;
    return right;
  endfunction

  function automatic word_t branch_read(ref word_t left, const ref word_t right, input bit choose);
    // verilator no_inline_task
    word_t seen;
    left = 7;
    if (choose) left = 11;
    else left = 13;
    seen = right;
    left = 19;
    return seen;
  endfunction

`ifdef FOURSTATE_LIFE_ALIAS
  typedef logic [64:0] wide_t;
  wide_t wide_words[2];
  wide_t wide_result;
  wide_t wide_value;
  wide_t wide_other;
  localparam wide_t LEFT_PATTERN = {5'b001xz, 60'h123_4567_89ab_cdef};
  localparam wide_t OTHER_PATTERN = {5'b11111, 60'hfed_cba9_8765_4321};
  localparam wide_t UPDATED_LEFT = {5'b10zx1, 60'h123_4567_89ab_cdef};
  localparam wide_t UPDATED_OTHER = {5'b10zx1, 60'hfed_cba9_8765_4321};
  localparam wide_t LAST_PATTERN = {5'bz10x1, 60'h987_6543_210f_edcb};

  function automatic wide_t mixed_write(ref wide_t left, ref wide_t right);
    left = LEFT_PATTERN;
    right[64:60] = 5'b10zx1;
    return left;
  endfunction

  function automatic wide_t mixed_middle(ref wide_t left, const ref wide_t right);
    // verilator no_inline_task
    wide_t seen;
    left = LEFT_PATTERN;
    seen = right;
    left = LAST_PATTERN;
    return seen;
  endfunction
`endif

  initial begin
    if (!$value$plusargs("cycles=%d", cycles)) cycles = 8;
    if (!$value$plusargs("case=%d", selected_case)) selected_case = 0;
    if (cycles !== 8 || selected_case < 0 || selected_case > 5) `stop;
    expected_checks = selected_case == 0 ? 192 : 48;
    expected_calls = selected_case == 0 ? 64 : 16;
`ifdef FOURSTATE_LIFE_ALIAS
    if (selected_case == 0) begin
      expected_checks = 288;
      expected_calls = 96;
    end
    else if (selected_case == 5) begin
      expected_checks = 96;
      expected_calls = 32;
    end
`else
    if (selected_case == 5) `stop;
`endif
    for (int cycle = 0; cycle < cycles; ++cycle) begin
      index_value = int'(cycle[0]);
      other_index = 1 - index_value;
      if (selected_case == 0 || selected_case == 1) begin
        words[0] = 222;
        words[1] = 222;
        result = read_left(words[index_value], words[index_value]);
        ++calls;
        `checkh(result, 18)
        `checkh(words[index_value], 18)
        `checkh(words[other_index], 222)
        words[0] = 222;
        words[1] = 222;
        result = read_left(words[index_value], words[other_index]);
        ++calls;
        `checkh(result, 17)
        `checkh(words[index_value], 17)
        `checkh(words[other_index], 223)
      end
      if (selected_case == 0 || selected_case == 2) begin
        left_value = 222;
        other_value = 222;
        result = middle_read(left_value, left_value);
        ++calls;
        `checkh(result, 17)
        `checkh(left_value, 29)
        `checkh(other_value, 222)
        left_value = 222;
        other_value = 222;
        result = middle_read(left_value, other_value);
        ++calls;
        `checkh(result, 222)
        `checkh(left_value, 29)
        `checkh(other_value, 222)
      end
      if (selected_case == 0 || selected_case == 3) begin
        words[0] = 222;
        words[1] = 222;
        result = reverse_write(words[index_value], words[index_value]);
        ++calls;
        `checkh(result, 13)
        `checkh(words[index_value], 13)
        `checkh(words[other_index], 222)
        words[0] = 222;
        words[1] = 222;
        result = reverse_write(words[index_value], words[other_index]);
        ++calls;
        `checkh(result, 11)
        `checkh(words[index_value], 224)
        `checkh(words[other_index], 11)
      end
      if (selected_case == 0 || selected_case == 4) begin
        left_value = 222;
        other_value = 222;
        result = branch_read(left_value, left_value, cycle[0]);
        ++calls;
        `checkh(result, cycle[0] ? 11 : 13)
        `checkh(left_value, 19)
        `checkh(other_value, 222)
        left_value = 222;
        other_value = 222;
        result = branch_read(left_value, other_value, cycle[0]);
        ++calls;
        `checkh(result, 222)
        `checkh(left_value, 19)
        `checkh(other_value, 222)
      end
`ifdef FOURSTATE_LIFE_ALIAS
      if (selected_case == 0 || selected_case == 5) begin
        wide_words[0] = OTHER_PATTERN;
        wide_words[1] = OTHER_PATTERN;
        wide_result = mixed_write(wide_words[index_value], wide_words[index_value]);
        ++calls;
        `checkh(wide_result, UPDATED_LEFT)
        `checkh(wide_words[index_value], UPDATED_LEFT)
        `checkh(wide_words[other_index], OTHER_PATTERN)
        wide_words[0] = OTHER_PATTERN;
        wide_words[1] = OTHER_PATTERN;
        wide_result = mixed_write(wide_words[index_value], wide_words[other_index]);
        ++calls;
        `checkh(wide_result, LEFT_PATTERN)
        `checkh(wide_words[index_value], LEFT_PATTERN)
        `checkh(wide_words[other_index], UPDATED_OTHER)
        wide_value = OTHER_PATTERN;
        wide_other = OTHER_PATTERN;
        wide_result = mixed_middle(wide_value, wide_value);
        ++calls;
        `checkh(wide_result, LEFT_PATTERN)
        `checkh(wide_value, LAST_PATTERN)
        `checkh(wide_other, OTHER_PATTERN)
        wide_value = OTHER_PATTERN;
        wide_other = OTHER_PATTERN;
        wide_result = mixed_middle(wide_value, wide_other);
        ++calls;
        `checkh(wide_result, OTHER_PATTERN)
        `checkh(wide_value, LAST_PATTERN)
        `checkh(wide_other, OTHER_PATTERN)
      end
`endif
    end
    if (checks !== expected_checks || calls !== expected_calls) `stop;
    $display("LIFE_REF_ALIAS_PASS checks=%0d calls=%0d cycles=%0d", checks, calls, cycles);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
