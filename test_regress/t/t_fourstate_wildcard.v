// DESCRIPTION: Verilator: Wildcard equality known mismatches dominate unknown bits
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "width=%0d check=%0d line=%0d got=%b expected=%b", WIDTH, checks, `__LINE__, (gotv), (expv)); end while (0)
// verilog_format: on

module t;
  wire [4:0] done;
  wire [31:0] checks[5];
  wildcard_check #(2) w2(done[0], checks[0]);
  wildcard_check #(7) w7(done[1], checks[1]);
  wildcard_check #(33) w33(done[2], checks[2]);
  wildcard_check #(65) w65(done[3], checks[3]);
  wildcard_check #(95) w95(done[4], checks[4]);
  initial begin
    #257;
    if (done !== 5'b11111) $fatal(1, "Wildcard workers did not complete: %b", done);
    $display("Wildcard checks: %0d", checks[0]+checks[1]+checks[2]+checks[3]+checks[4]);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module wildcard_check #(parameter WIDTH = 2)(output bit done, output int checks = 0);
  localparam logic CONST_EQ = 2'b1x ==? 2'b00;
  localparam logic CONST_NEQ = 2'b1z !=? 2'b00;
  logic [WIDTH-1:0] lhs, rhs;

  function automatic logic state_bit(input int value);
    case (value)
      0: return 1'b0;
      1: return 1'b1;
      2: return 1'bx;
      3: return 1'bz;
    endcase
    return 1'bx;
  endfunction

  // Independent per-bit oracle: RHS X/Z is ignored; a known mismatch is decisive.
  function automatic logic expected_eq(input logic [WIDTH-1:0] a, b);
    bit unknown_bit = 0;
    bit mismatch = 0;
    for (int k = 0; k < WIDTH; k++) begin
      if ((b[k] === 1'b0) || (b[k] === 1'b1)) begin
        if ((a[k] === 1'bx) || (a[k] === 1'bz)) unknown_bit = 1;
        else if (a[k] !== b[k]) mismatch = 1;
      end
    end
    if (mismatch) return 1'b0;
    if (unknown_bit) return 1'bx;
    return 1'b1;
  endfunction

  initial begin
    `checkh(CONST_EQ, 1'b0);
    `checkh(CONST_NEQ, 1'b1);
    for (int i = 0; i < 16; i++) begin
      for (int j = 0; j < 16; j++) begin
        lhs = '0;
        rhs = '0;
        lhs[0] = state_bit(i % 4);
        lhs[WIDTH-1] = state_bit(i / 4);
        rhs[0] = state_bit(j % 4);
        rhs[WIDTH-1] = state_bit(j / 4);
        #1;
        `checkh(lhs ==? rhs, expected_eq(lhs, rhs));
        `checkh(lhs !=? rhs, ~expected_eq(lhs, rhs));
      end
    end
    done = 1;
  end
endmodule
