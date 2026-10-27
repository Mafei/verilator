// SPDX-License-Identifier: CC0-1.0
// UNEXECUTED: real typos at a parameterized top retain the original error/suggestion.
module t #(parameter N = 1);
  reg foobar;
  task boobar;
  endtask
  initial begin
    if (foobat) $stop;
    boobat;
  end
endmodule
