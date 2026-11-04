// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Isolate aliased SV ref parameters, with all instrumentation passed explicitly.
module alias_explicit_control;
  typedef bit [31:0] key_t;
  key_t selected[2];
  key_t calls = 0;
  key_t result_left;
  key_t result_right;
  key_t element_left;
  key_t element_right;
  int index_value;
  function automatic key_t read_left(ref key_t left, ref key_t right, ref key_t count);
    ++count;
    left = 17;
    right = right + 1;
    return left;
  endfunction
  function automatic key_t read_right(ref key_t left, ref key_t right, ref key_t count);
    ++count;
    left = 17;
    right = right + 1;
    return right;
  endfunction
  initial begin
    if (!$value$plusargs("index=%d", index_value)) index_value = 1;
    selected[1] = 222;
    result_left = read_left(selected[index_value], selected[index_value], calls);
    element_left = selected[1];
    selected[1] = 222;
    result_right = read_right(selected[index_value], selected[index_value], calls);
    element_right = selected[1];
    $display("ALIAS_EXPLICIT left_return=%0d left_element=%0d right_return=%0d right_element=%0d calls=%0d expected=18", result_left, element_left, result_right, element_right, calls);
    if (result_left !== 18 || element_left !== 18 || result_right !== 18 || element_right !== 18 || calls !== 2) $fatal(1, "SV ref alias differs");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
