// DESCRIPTION: Verilator: Four-state resolver literal truth tables
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Tables use state order 0, 1, X, Z. No compiler value/mask representation
// is used by this oracle. kind 0 is wire/tri, 1 is wor, and 2 is wand.
// verilog_format: off
`ifndef FOURSTATE_RESOLVE_CHECKS
`define FOURSTATE_RESOLVE_CHECKS
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkr(gotv,expv) do begin checks++; if ((gotv) != (expv)) begin $write("%%Error: %s:%0d: got=%0.3f expected=%0.3f\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
`endif
// verilog_format: on

function automatic logic state_code(input int code);
  case (code)
    0: return 1'b0;
    1: return 1'b1;
    2: return 1'bx;
    3: return 1'bz;
    default: return 1'bx;
  endcase
endfunction

function automatic int state_index(input logic value);
  case (value)
    1'b0: return 0;
    1'b1: return 1;
    1'bx: return 2;
    1'bz: return 3;
  endcase
  return 2;
endfunction

function automatic logic pair_literal(input int kind, input int index);
  case (kind)
    0: case (index)
      0: return 1'b0;
      1: return 1'bx;
      2: return 1'bx;
      3: return 1'b0;
      4: return 1'bx;
      5: return 1'b1;
      6: return 1'bx;
      7: return 1'b1;
      8: return 1'bx;
      9: return 1'bx;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'b0;
      13: return 1'b1;
      14: return 1'bx;
      15: return 1'bz;
      default: return 1'bx;
    endcase
    1: case (index)
      0: return 1'b0;
      1: return 1'b1;
      2: return 1'bx;
      3: return 1'b0;
      4: return 1'b1;
      5: return 1'b1;
      6: return 1'b1;
      7: return 1'b1;
      8: return 1'bx;
      9: return 1'b1;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'b0;
      13: return 1'b1;
      14: return 1'bx;
      15: return 1'bz;
      default: return 1'bx;
    endcase
    2: case (index)
      0: return 1'b0;
      1: return 1'b0;
      2: return 1'b0;
      3: return 1'b0;
      4: return 1'b0;
      5: return 1'b1;
      6: return 1'bx;
      7: return 1'b1;
      8: return 1'b0;
      9: return 1'bx;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'b0;
      13: return 1'b1;
      14: return 1'bx;
      15: return 1'bz;
      default: return 1'bx;
    endcase
    default: return 1'bx;
  endcase
endfunction

function automatic logic triple_literal(input int kind, input int index);
  case (kind)
    0: case (index)
      0: return 1'b0;
      1: return 1'bx;
      2: return 1'bx;
      3: return 1'b0;
      4: return 1'bx;
      5: return 1'bx;
      6: return 1'bx;
      7: return 1'bx;
      8: return 1'bx;
      9: return 1'bx;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'b0;
      13: return 1'bx;
      14: return 1'bx;
      15: return 1'b0;
      16: return 1'bx;
      17: return 1'bx;
      18: return 1'bx;
      19: return 1'bx;
      20: return 1'bx;
      21: return 1'b1;
      22: return 1'bx;
      23: return 1'b1;
      24: return 1'bx;
      25: return 1'bx;
      26: return 1'bx;
      27: return 1'bx;
      28: return 1'bx;
      29: return 1'b1;
      30: return 1'bx;
      31: return 1'b1;
      32: return 1'bx;
      33: return 1'bx;
      34: return 1'bx;
      35: return 1'bx;
      36: return 1'bx;
      37: return 1'bx;
      38: return 1'bx;
      39: return 1'bx;
      40: return 1'bx;
      41: return 1'bx;
      42: return 1'bx;
      43: return 1'bx;
      44: return 1'bx;
      45: return 1'bx;
      46: return 1'bx;
      47: return 1'bx;
      48: return 1'b0;
      49: return 1'bx;
      50: return 1'bx;
      51: return 1'b0;
      52: return 1'bx;
      53: return 1'b1;
      54: return 1'bx;
      55: return 1'b1;
      56: return 1'bx;
      57: return 1'bx;
      58: return 1'bx;
      59: return 1'bx;
      60: return 1'b0;
      61: return 1'b1;
      62: return 1'bx;
      63: return 1'bz;
      default: return 1'bx;
    endcase
    1: case (index)
      0: return 1'b0;
      1: return 1'b1;
      2: return 1'bx;
      3: return 1'b0;
      4: return 1'b1;
      5: return 1'b1;
      6: return 1'b1;
      7: return 1'b1;
      8: return 1'bx;
      9: return 1'b1;
      10: return 1'bx;
      11: return 1'bx;
      12: return 1'b0;
      13: return 1'b1;
      14: return 1'bx;
      15: return 1'b0;
      16: return 1'b1;
      17: return 1'b1;
      18: return 1'b1;
      19: return 1'b1;
      20: return 1'b1;
      21: return 1'b1;
      22: return 1'b1;
      23: return 1'b1;
      24: return 1'b1;
      25: return 1'b1;
      26: return 1'b1;
      27: return 1'b1;
      28: return 1'b1;
      29: return 1'b1;
      30: return 1'b1;
      31: return 1'b1;
      32: return 1'bx;
      33: return 1'b1;
      34: return 1'bx;
      35: return 1'bx;
      36: return 1'b1;
      37: return 1'b1;
      38: return 1'b1;
      39: return 1'b1;
      40: return 1'bx;
      41: return 1'b1;
      42: return 1'bx;
      43: return 1'bx;
      44: return 1'bx;
      45: return 1'b1;
      46: return 1'bx;
      47: return 1'bx;
      48: return 1'b0;
      49: return 1'b1;
      50: return 1'bx;
      51: return 1'b0;
      52: return 1'b1;
      53: return 1'b1;
      54: return 1'b1;
      55: return 1'b1;
      56: return 1'bx;
      57: return 1'b1;
      58: return 1'bx;
      59: return 1'bx;
      60: return 1'b0;
      61: return 1'b1;
      62: return 1'bx;
      63: return 1'bz;
      default: return 1'bx;
    endcase
    2: case (index)
      0: return 1'b0;
      1: return 1'b0;
      2: return 1'b0;
      3: return 1'b0;
      4: return 1'b0;
      5: return 1'b0;
      6: return 1'b0;
      7: return 1'b0;
      8: return 1'b0;
      9: return 1'b0;
      10: return 1'b0;
      11: return 1'b0;
      12: return 1'b0;
      13: return 1'b0;
      14: return 1'b0;
      15: return 1'b0;
      16: return 1'b0;
      17: return 1'b0;
      18: return 1'b0;
      19: return 1'b0;
      20: return 1'b0;
      21: return 1'b1;
      22: return 1'bx;
      23: return 1'b1;
      24: return 1'b0;
      25: return 1'bx;
      26: return 1'bx;
      27: return 1'bx;
      28: return 1'b0;
      29: return 1'b1;
      30: return 1'bx;
      31: return 1'b1;
      32: return 1'b0;
      33: return 1'b0;
      34: return 1'b0;
      35: return 1'b0;
      36: return 1'b0;
      37: return 1'bx;
      38: return 1'bx;
      39: return 1'bx;
      40: return 1'b0;
      41: return 1'bx;
      42: return 1'bx;
      43: return 1'bx;
      44: return 1'b0;
      45: return 1'bx;
      46: return 1'bx;
      47: return 1'bx;
      48: return 1'b0;
      49: return 1'b0;
      50: return 1'b0;
      51: return 1'b0;
      52: return 1'b0;
      53: return 1'b1;
      54: return 1'bx;
      55: return 1'b1;
      56: return 1'b0;
      57: return 1'bx;
      58: return 1'bx;
      59: return 1'bx;
      60: return 1'b0;
      61: return 1'b1;
      62: return 1'bx;
      63: return 1'bz;
      default: return 1'bx;
    endcase
    default: return 1'bx;
  endcase
endfunction
