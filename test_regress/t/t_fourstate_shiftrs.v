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
  wire [4:0] done;
  shift_check #(.WIDTH(7)) c7(clk, done[0]);
  shift_check #(.WIDTH(31)) c31(clk, done[1]);
  shift_check #(.WIDTH(48)) c48(clk, done[2]);
  shift_check #(.WIDTH(65)) c65(clk, done[3]);
  shift_check #(.WIDTH(95)) c95(clk, done[4]);

  always @(posedge clk) begin
    if (&done) begin
      $display("Shift checks: %0d", c7.checks + c31.checks + c48.checks + c65.checks + c95.checks);
      $write("*-* All Finished *-*\n");
      $finish;
    end
  end
endmodule

module shift_check #(parameter WIDTH = 7) (input clk, output bit done = 0);
  int unsigned cycle = 0;
  int unsigned checks = 0;
  logic signed [WIDTH-1:0] data;
  logic [WIDTH-1:0] unsigned_data;
  logic [32:0] distance;
  logic [64:0] wide_distance;
  logic signed [WIDTH-1:0] result;
  logic [WIDTH-1:0] unsigned_result;
  logic [WIDTH-1:0] expected;
  logic [WIDTH-1:0] unsigned_expected;
  typedef logic signed [WIDTH+4:0] widened_t;
  widened_t widened;
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

  function automatic logic signed [WIDTH-1:0] unknown_data();
    calls = calls + 1;
    return data;
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
        wide_distance = 65'(amount);
        result = data >>> wide_distance;
        `checkh(result, expected);
      end

      distance = 33'h100000000;
      result = data >>> distance;
      `checkh(result, {WIDTH{data[WIDTH-1]}});
      `checkh(unsigned_data >>> distance, {WIDTH{1'b0}});
      wide_distance = 65'h10000000000000000;
      result = data >>> wide_distance;
      `checkh(result, {WIDTH{data[WIDTH-1]}});
      `checkh(unsigned_data >>> wide_distance, {WIDTH{1'b0}});

      distance = 33'd1;
      widened = widened_t'(data) >>> distance;
      `checkh(widened, {{6{data[WIDTH-1]}}, data[WIDTH-1:1]});

      distance = 'x;
      result = data >>> distance;
      `checkh(result, {WIDTH{1'bx}});
      `checkh(unsigned_data >>> distance, {WIDTH{1'bx}});
      distance = 'z;
      result = data >>> distance;
      `checkh(result, {WIDTH{1'bx}});
      wide_distance = '0;
      wide_distance[64] = 1'bx;
      `checkh(data >>> wide_distance, {WIDTH{1'bx}});

      calls = 0;
      result = data >>> next_count();
      `checkh(result, {data[WIDTH-1], data[WIDTH-1:1]});
      `checkh(calls, 32'd1);
      calls = 0;
      result = unknown_data() >>> next_count();
      `checkh(result, {data[WIDTH-1], data[WIDTH-1:1]});
      `checkh(calls, 32'd2);
      calls = 0;
      `checkh($isunknown(known_data() >>> distance), 1'b1);
      `checkh(calls, 32'd1);
      calls = 0;
      `checkh($isunknown(known_data() >>> next_count()), 1'b0);
      `checkh(calls, 32'd2);
      calls = 0;
      result = known_data() >>> distance;
      `checkh(result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);
      calls = 0;
      result = data >>> unknown_count();
      `checkh(result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);
      calls = 0;
      result = known_data() << distance;
      `checkh(result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);
      calls = 0;
      result = known_data() >> distance;
      `checkh(result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);
      calls = 0;
      result = data << next_count();
      `checkh(result, {data[WIDTH-2:0], 1'b0});
      `checkh(calls, 32'd1);
      calls = 0;
      result = data >> next_count();
      `checkh(result, {1'b0, data[WIDTH-1:1]});
      `checkh(calls, 32'd1);
      calls = 0;
      unsigned_result = unsigned_data >>> next_count();
      `checkh(unsigned_result, {1'b0, data[WIDTH-1:1]});
      `checkh(calls, 32'd1);
      calls = 0;
      unsigned_result = $unsigned(known_data()) >>> distance;
      `checkh(unsigned_result, {WIDTH{1'bx}});
      `checkh(calls, 32'd1);
      calls = 0;
      `checkh($isunknown(known_data() << distance), 1'b1);
      `checkh(calls, 32'd1);
      calls = 0;
      `checkh($isunknown(known_data() >> distance), 1'b1);
      `checkh(calls, 32'd1);

      if (cycle == 8) done = 1;
    end
  end
endmodule
