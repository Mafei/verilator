// DESCRIPTION: Verilator: Debug emission of function and task arguments
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t (
    input int left,
    input int right,
    output int result
);
  function automatic int pair(input int first, input int second);
    return first * 101 + second;
  endfunction

  function automatic int single(input int value);
    return value;
  endfunction

  function automatic int empty();
    return 7;
  endfunction

  function automatic int defaults(input int first, input int second = 17);
    return first + second;
  endfunction

  task automatic save(input int first, input int second, inout int value);
    value += first + second;
  endtask

  always_comb begin
    result = pair(left, right) + pair(.second(left), .first(right));
    result += pair(single(left), pair(right, left));
    result += defaults(left) + defaults(left,) + single(right) + empty();
    save(left, right, result);
  end
endmodule
