// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv, expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define checkh(gotv, expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%h expected=%h\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

module t;
  wire [3:0] wide_done;
  case_wide #(.WIDTH(7)) w7(wide_done[0]);
  case_wide #(.WIDTH(33)) w33(wide_done[1]);
  case_wide #(.WIDTH(65)) w65(wide_done[2]);
  case_wide #(.WIDTH(95)) w95(wide_done[3]);
  logic [2:0] selector;
  bit [2:0] known_selector;
  int calls;
  int actual;
  int expected;
  logic [2:0] pattern;

  function automatic logic [2:0] selected();
    calls++;
    return selector;
  endfunction

  function automatic logic decode(input int index);
    case (index)
      0: return 1'b0;
      1: return 1'b1;
      2: return 1'bx;
      default: return 1'bz;
    endcase
  endfunction

  task automatic test_casex();
    expected = 0;
    pattern = 3'b11x;
    for (int b = 0; b < 3; b++) begin
      if (selector[b] !== 1'bx && selector[b] !== 1'bz
          && pattern[b] !== 1'bx && pattern[b] !== 1'bz
          && selector[b] !== pattern[b]) expected = 1;
    end
    casex (selected())
      3'b11x: actual = 0;
      default: actual = 1;
    endcase
    `checkd(actual, expected);
  endtask

  task automatic test_casez();
    expected = 0;
    pattern = 3'b1zx;
    for (int b = 0; b < 3; b++) begin
      if (selector[b] !== 1'bz && pattern[b] !== 1'bz
          && selector[b] !== pattern[b]) expected = 1;
    end
    casez (selected())
      3'b1zx: actual = 0;
      default: actual = 1;
    endcase
    `checkd(actual, expected);
  endtask

  initial begin
    calls = 0;
    for (int index = 0; index < 64; index++) begin
      selector = {decode(index / 16), decode((index / 4) % 4), decode(index % 4)};
      #1;
      expected = selector === 3'b11x ? 0 : 1;
      case (selected())
        3'b11x: actual = 0;
        default: actual = 1;
      endcase
      `checkd(actual, expected);
      expected = selector === 3'b11z ? 0 : 1;
      case (selected())
        3'b11z: actual = 0;
        default: actual = 1;
      endcase
      `checkd(actual, expected);
      test_casex();
      test_casez();
      `checkd(calls, (index + 1) * 4);
    end
    for (int index = 0; index < 8; index++) begin
      known_selector = 3'(index);
      #1;
      casex (known_selector)
        3'b1zz: actual = 1;
        3'bxxx: actual = 2;
        default: actual = 3;
      endcase
      `checkd(actual, index >= 4 ? 1 : 2);
      case (known_selector)
        3'bxxx, 3'bzzz: actual = 1;
        default: actual = 2;
      endcase
      `checkd(actual, 2);
    end
    wait (&wide_done);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module case_wide #(parameter WIDTH = 7) (output bit done = 0);
  logic [WIDTH-1:0] selector;
  int actual;
  int calls = 0;

  function automatic logic [WIDTH-1:0] selected();
    calls++;
    return selector;
  endfunction

  initial begin
    for (int index = 0; index < 16; index++) begin
      selector = '1;
      selector[0] = index[0] ? 1'bz : 1'bx;
      selector[WIDTH-1] = index[1] ? 1'bx : 1'bz;
      if (index[2]) selector[WIDTH/2] = 1'b0;
      #1;
      casex (selected())
        {1'bx, {WIDTH-2{1'b1}}, 1'bz}, '0: begin
          case (1'bx)
            1'bz: actual = 3;
            1'bx: actual = 1;
            default: actual = 4;
          endcase
        end
        default: actual = 2;
      endcase
      `checkd(actual, index[2] ? 2 : 1);
      `checkd(calls, index + 1);
      casez (selector)
        {1'bz, {WIDTH-2{1'b1}}, 1'bz}: actual = 1;
        default: actual = 2;
      endcase
      `checkd(actual, index[2] ? 2 : 1);
    end
    done = 1;
  end
endmodule
