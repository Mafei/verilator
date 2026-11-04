// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Original alias-test instrumentation isolated from associative methods.
module alias_external_control;
  typedef bit [31:0] key_t;
  key_t selected_index[2];
  int alias_calls = 0;
  int index_value;
  int result;
  function automatic int alias_once(ref key_t left, ref key_t right);
    ++alias_calls;
    left = 17;
    right = right + 1;
    return int'(left);
  endfunction
  initial begin
    if (!$value$plusargs("index=%d", index_value)) index_value = 1;
    result = alias_once(selected_index[index_value], selected_index[index_value]);
    if (result !== 18 || selected_index[1] !== 18 || alias_calls !== 1) $fatal(1, "Alias differs");
    $display("ALIAS_EXTERNAL_PASS");
    $finish;
  end
endmodule
