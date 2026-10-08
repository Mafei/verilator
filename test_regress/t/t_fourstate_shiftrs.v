// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t (input clk);
  wire [3:0] done;
  shift_check #(.WIDTH(7)) c7(clk, done[0]);
  shift_check #(.WIDTH(31)) c31(clk, done[1]);
  shift_check #(.WIDTH(48)) c48(clk, done[2]);
  shift_check #(.WIDTH(65)) c65(clk, done[3]);

  always @(posedge clk) begin
    if (&done) begin
      $write("*-* All Finished *-*\n");
      $finish;
    end
  end
endmodule

module shift_check #(parameter WIDTH = 7) (input clk, output bit done = 0);
  int unsigned cycle = 0;
  logic signed [WIDTH-1:0] data;
  logic [WIDTH-1:0] unsigned_data;
  logic [32:0] distance;
  logic signed [WIDTH-1:0] result;
  logic [WIDTH-1:0] unsigned_result;
  logic [WIDTH-1:0] expected;
  logic [WIDTH-1:0] unsigned_expected;
  logic signed [WIDTH+4:0] widened;
  bit [31:0] calls;

  function automatic bit [32:0] next_count();
    calls = calls + 1;
    return 33'd1;
  endfunction

  function automatic bit signed [WIDTH-1:0] known_data();
    calls = calls + 1;
    return WIDTH'(cycle * 13);
  endfunction

  function automatic logic [32:0] unknown_count();
    calls = calls + 1;
    return 'x;
  endfunction

  always @(posedge clk) begin
    if (!done) begin
      cycle = cycle + 1;
      data = WIDTH'(cycle * 13);
      data[WIDTH/2] = 1'bx;
      data[2] = 1'bz;
      case (cycle[1:0])
        0: data[WIDTH-1] = 1'b0;
        1: data[WIDTH-1] = 1'b1;
        2: data[WIDTH-1] = 1'bx;
        3: data[WIDTH-1] = 1'bz;
      endcase
      unsigned_data = data;

      // Bit-by-bit selection is an independent oracle; it does not use >>>.
      for (int amount = 0; amount <= WIDTH + 2; amount++) begin
        distance = 33'(amount);
        for (int position = 0; position < WIDTH; position++) begin
          if (position + amount < WIDTH) begin
            expected[position] = data[position + amount];
            unsigned_expected[position] = data[position + amount];
          end else begin
            expected[position] = data[WIDTH-1];
            unsigned_expected[position] = 1'b0;
          end
        end
        result = data >>> distance;
        unsigned_result = unsigned_data >>> distance;
        `checkh(result, expected);
        `checkh(unsigned_result, unsigned_expected);
        `checkh(data >> distance, unsigned_expected);
      end

      distance = 33'h100000000;
      result = data >>> distance;
      `checkh(result, {WIDTH{data[WIDTH-1]}});
      `checkh(unsigned_data >>> distance, {WIDTH{1'b0}});

      distance = 33'd1;
      widened = data >>> distance;
      `checkh(widened, {{6{data[WIDTH-1]}}, data[WIDTH-1:1]});

      distance = 'x;
      result = data >>> distance;
      `checkh(result, {WIDTH{1'bx}});
      `checkh(unsigned_data >>> distance, {WIDTH{1'bx}});
      distance = 'z;
      result = data >>> distance;
      `checkh(result, {WIDTH{1'bx}});

      calls = 0;
      result = data >>> next_count();
      `checkh(result, {data[WIDTH-1], data[WIDTH-1:1]});
      `checkh(calls, 32'd1);
      calls = 0;
      result = known_data() >>> distance;
      `checkh(result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);
      calls = 0;
      result = data >>> unknown_count();
      `checkh(result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);

      if (cycle == 8) done = 1;
    end
  end
endmodule
