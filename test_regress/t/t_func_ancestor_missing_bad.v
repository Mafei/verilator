// SPDX-License-Identifier: CC0-1.0
// UNEXECUTED: a missing task remains a user-code error after context preflight.
module leaf;
  initial absent_task();
endmodule
module t;
  leaf child0();
endmodule
