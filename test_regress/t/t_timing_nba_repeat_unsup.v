// DESCRIPTION: Verilator: Repeat controls outside procedural assignment support remain unsupported
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  event first_event;
  event second_event;
  logic q;
  initial begin
    ->> repeat(2) @first_event second_event;
    assign q = repeat(2) @first_event 1'b1;
  end
endmodule
