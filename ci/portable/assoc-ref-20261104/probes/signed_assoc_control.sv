// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Public isolation of signed-key ordering; separate from reference bounds.
module signed_assoc_control;
  typedef bit signed [31:0] key_t;
  bit [7:0] data[key_t];
  key_t selected;
  int result;
  initial begin
    data[-5] = 1;
    data[0] = 2;
    data[5] = 3;
    result = data.first(selected);
    $display("SIGNED_ASSOC_FIRST got=%0d expected=-5 result=%0d", selected, result);
    if (result !== 1 || selected !== -5) $fatal(1, "Signed associative key ordering differs");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
