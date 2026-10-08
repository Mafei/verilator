// DESCRIPTION: Verilator: Four-state isolated drive semantics
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

function automatic logic drive_state(input int code);
  case (code)
    0: return 1'b0;
    1: return 1'b1;
    2: return 1'bx;
    3: return 1'bz;
    default: return 1'bx;
  endcase
endfunction

// Literal primitive tables: enable row and data column, state order 0/1/X/Z.
function automatic logic drive_literal(input int kind, input int index);
  case (kind)
    0:
    case (index)
      0: return 1'bz;
      1: return 1'bz;
      2: return 1'bz;
      3: return 1'bz;
      4: return 1'b0;
      5: return 1'b1;
      6: return 1'bx;
      7: return 1'bx;
      8: return 1'bx;
      9: return 1'bx;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'bx;
      13: return 1'bx;
      14: return 1'bx;
      15: return 1'bx;
      default: return 1'bx;
    endcase
    1:
    case (index)
      0: return 1'b0;
      1: return 1'b1;
      2: return 1'bx;
      3: return 1'bx;
      4: return 1'bz;
      5: return 1'bz;
      6: return 1'bz;
      7: return 1'bz;
      8: return 1'bx;
      9: return 1'bx;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'bx;
      13: return 1'bx;
      14: return 1'bx;
      15: return 1'bx;
      default: return 1'bx;
    endcase
    2:
    case (index)
      0: return 1'bz;
      1: return 1'bz;
      2: return 1'bz;
      3: return 1'bz;
      4: return 1'b1;
      5: return 1'b0;
      6: return 1'bx;
      7: return 1'bx;
      8: return 1'bx;
      9: return 1'bx;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'bx;
      13: return 1'bx;
      14: return 1'bx;
      15: return 1'bx;
      default: return 1'bx;
    endcase
    3:
    case (index)
      0: return 1'b1;
      1: return 1'b0;
      2: return 1'bx;
      3: return 1'bx;
      4: return 1'bz;
      5: return 1'bz;
      6: return 1'bz;
      7: return 1'bz;
      8: return 1'bx;
      9: return 1'bx;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'bx;
      13: return 1'bx;
      14: return 1'bx;
      15: return 1'bx;
      default: return 1'bx;
    endcase
    default: return 1'bx;
  endcase
endfunction
