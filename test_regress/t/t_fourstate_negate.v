// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks = checks + 1; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  bit clk = 0;
  always #5 clk = ~clk;
  wire [6:0] done;
  negate_check #(
      .WIDTH(1)
  ) c1 (
      clk,
      done[0]
  );
  negate_check #(
      .WIDTH(7)
  ) c7 (
      clk,
      done[1]
  );
  negate_check #(
      .WIDTH(25)
  ) c25 (
      clk,
      done[2]
  );
  negate_check #(
      .WIDTH(33)
  ) c33 (
      clk,
      done[3]
  );
  negate_check #(
      .WIDTH(65)
  ) c65 (
      clk,
      done[4]
  );
  negate_check #(
      .WIDTH(95)
  ) c95 (
      clk,
      done[5]
  );
  negate_check #(
      .WIDTH(129)
  ) c129 (
      clk,
      done[6]
  );
  always @(posedge clk) begin
    if (&done) begin
      $display(
          "Negate checks: %0d",
          c1.checks + c7.checks + c25.checks + c33.checks + c65.checks + c95.checks + c129.checks);
      $write("*-* All Finished *-*\n");
      $finish;
    end
  end
endmodule

module negate_check #(
    parameter WIDTH = 7
) (
    input clk,
    output bit done = 0
);
  int unsigned cycle = 0;
  int unsigned checks = 0;
  int unsigned calls = 0;
  logic signed [WIDTH-1:0] data;
  logic signed [0:WIDTH-1] ascending;
  logic [WIDTH-1:0] result;
  logic [WIDTH-1:0] expected;
  typedef logic signed [WIDTH+4:0] widened_t;
  widened_t widened_input;
  widened_t widened_result;
  widened_t widened_expected;
  bit carry;
  bit unknown_result;
  bit [WIDTH-1:0] two_state_result;

  function automatic logic signed [WIDTH-1:0] once_value();
    calls = calls + 1;
    return data;
  endfunction

  always @(posedge clk) begin
    if (!done) begin
      cycle = cycle + 1;
      data = WIDTH'(cycle * 13);
      if (cycle == 1) data = '0;
      if (cycle == 2) data = '1;
      if (cycle == 3) begin
        data = '0;
        data[WIDTH-1] = 1'b1;
      end
      ascending = data;
      // Independent ripple complement/increment oracle, without unary minus.
      carry = 1;
      for (int i = 0; i < WIDTH; i++) begin
        expected[i] = ~data[i] ^ carry;
        carry = ~data[i] & carry;
      end
      result = -data;
      `checkh(result, expected);
      result = -ascending;
      `checkh(result, expected);
      // Assignment context must widen the signed operand before negation.
      widened_input = data;
      carry = 1;
      for (int i = 0; i < WIDTH + 5; i++) begin
        widened_expected[i] = ~widened_input[i] ^ carry;
        carry = ~widened_input[i] & carry;
      end
      widened_result = -data;
      `checkh(widened_result, widened_expected);
      calls = 0;
      result = -once_value();
      `checkh(result, expected);
      `checkh(calls, 32'd1);
      calls = 0;
      unknown_result = (-once_value()) === {WIDTH{1'bx}};
      `checkh(unknown_result, 1'b0);
      `checkh(calls, 32'd1);
      data[WIDTH/2] = 1'bx;
      result = -data;
      `checkh(result, {WIDTH{1'bx}});
      calls = 0;
      result = -once_value();
      `checkh(result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);
      calls = 0;
      unknown_result = (-once_value()) === {WIDTH{1'bx}};
      `checkh(unknown_result, 1'b1);
      `checkh(calls, 32'd1);
      calls = 0;
      two_state_result = -once_value();
      `checkh(two_state_result, {WIDTH{1'b0}});
      `checkh(calls, 32'd1);
      data[WIDTH/2] = 1'bz;
      result = -data;
      `checkh(result, {WIDTH{1'bx}});
      calls = 0;
      unknown_result = (-once_value()) === {WIDTH{1'bx}};
      `checkh(unknown_result, 1'b1);
      `checkh(calls, 32'd1);
      if (cycle == 37) done = 1;
    end
  end
endmodule
