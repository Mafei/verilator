// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module t;
  typedef logic [31:0] index_t;
  logic [6:0] memory [3:1];
  index_t index;
  logic [6:0] data;
  logic [6:0] zero_memory [0:3];
  index_t zero_index;
  logic [6:0] ascending [1:3];
  logic [6:0] negative [-2:0];
  logic signed [31:0] signed_index;
  typedef logic [6:0] word_t;
  word_t matrix [1:2][3:1];
  index_t row_index;
  index_t column_index;
  int unsigned two_state_index;
  bit [31:0] index_calls = 0;
  bit [31:0] rhs_calls = 0;

  function automatic index_t selected_index();
    index_calls = index_calls + 1;
    return zero_index;
  endfunction

  function automatic logic [6:0] rhs_value();
    rhs_calls = rhs_calls + 1;
    return 7'h7f;
  endfunction

  initial begin
    memory[1] = 7'h11;
    memory[2] = 7'h22;
    memory[3] = 7'h33;
    for (int i = 0; i < 4; i++) zero_memory[i] = 7'(i + 10);
    ascending[1] = 7'h11;
    ascending[2] = 7'h22;
    ascending[3] = 7'h33;
    negative[-2] = 7'h11;
    negative[-1] = 7'h22;
    negative[0] = 7'h33;
    for (int r = 1; r <= 2; r++) begin
      for (int c = 1; c <= 3; c++) matrix[r][c] = 7'(r * 10 + c);
    end
    #1;
    index = 'x;
    data = memory[index];
    `checkh(data, 7'bxxxxxxx);
    memory[index] = 7'h7f;
    #1;
    `checkh(memory[1], 7'h11);
    `checkh(memory[2], 7'h22);
    `checkh(memory[3], 7'h33);

    zero_index = 32'h80000000;
    `checkh(zero_memory[zero_index], 7'bxxxxxxx);
    zero_memory[zero_index] = 7'h7f;
    zero_index = 32'bx0000000000000000000000000000000;
    `checkh(zero_memory[zero_index], 7'bxxxxxxx);
    zero_memory[zero_index] = 7'h7f;
    zero_index = 32'd4;
    `checkh(zero_memory[zero_index], 7'bxxxxxxx);
    zero_memory[zero_index] = 7'h7f;
    zero_index = 32'bxz;
    index_calls = 0;
    data = zero_memory[selected_index()];
    `checkh(data, 7'bxxxxxxx);
    `checkh(index_calls, 32'd1);
    index_calls = 0;
    rhs_calls = 0;
    zero_memory[selected_index()] <= rhs_value();
    #1;
    `checkh(index_calls, 32'd1);
    `checkh(rhs_calls, 32'd1);
    for (int i = 0; i < 4; i++) `checkh(zero_memory[i], 7'(i + 10));

    // Integer atom types are two-state; converting X/Z to int yields zero.
    two_state_index = int'(32'bxz);
    `checkh(zero_memory[two_state_index], 7'd10);

    // Snapshots for successive statements and functions must remain independent.
    zero_index = 'x;
    index_calls = 0;
    `checkh($isunknown(zero_memory[selected_index()]), 1'b1);
    `checkh(index_calls, 32'd1);
    zero_index = 32'd2;
    index_calls = 0;
    `checkh($isunknown(zero_memory[selected_index()]), 1'b0);
    `checkh(index_calls, 32'd1);

    zero_index = 'z;
    index_calls = 0;
    rhs_calls = 0;
    zero_memory[selected_index()] = rhs_value();
    `checkh(index_calls, 32'd1);
    `checkh(rhs_calls, 32'd1);
    for (int i = 0; i < 4; i++) `checkh(zero_memory[i], 7'(i + 10));

    signed_index = -32'sd1;
    `checkh(negative[signed_index], 7'h22);
    signed_index = 32'sd2;
    `checkh(ascending[signed_index], 7'h22);
    signed_index = -32'sd3;
    `checkh(negative[signed_index], 7'bxxxxxxx);
    negative[signed_index] = 7'h7f;
    signed_index = 'x;
    `checkh(ascending[signed_index], 7'bxxxxxxx);
    ascending[signed_index] = 7'h7f;
    #1;
    `checkh(negative[-2], 7'h11);
    `checkh(negative[-1], 7'h22);
    `checkh(negative[0], 7'h33);
    `checkh(ascending[1], 7'h11);
    `checkh(ascending[2], 7'h22);
    `checkh(ascending[3], 7'h33);

    row_index = 32'd1;
    column_index = 32'd2;
    `checkh(matrix[row_index][column_index], 7'd12);
    row_index = 'x;
    `checkh(matrix[row_index][column_index], 7'bxxxxxxx);
    matrix[row_index][column_index] = 7'h7f;
    row_index = 32'd1;
    column_index = 'z;
    `checkh(matrix[row_index][column_index], 7'bxxxxxxx);
    matrix[row_index][column_index] <= 7'h7f;
    #1;
    for (int r = 1; r <= 2; r++) begin
      for (int c = 1; c <= 3; c++) `checkh(matrix[r][c], 7'(r * 10 + c));
    end

    // A zero-based array exposes accidental X/Z-to-zero index conversion.
    zero_index = 32'bxz;
    data = zero_memory[zero_index];
    `checkh(data, 7'bxxxxxxx);
    zero_memory[zero_index] <= 7'h7f;
    #1;
    for (int i = 0; i < 4; i++) `checkh(zero_memory[i], 7'(i + 10));

    index = 32'd2;
    memory[index] <= 7'b10xz010;
    index = 32'd1;
    #1;
    `checkh(memory[2], 7'b10xz010);
    `checkh(memory[1], 7'h11);
    index = 32'd0;
    data = memory[index];
    `checkh(data, 7'bxxxxxxx);
    memory[index] = 7'h7f;
    #1;
    `checkh(memory[1], 7'h11);
    `checkh(memory[2], 7'b10xz010);
    `checkh(memory[3], 7'h33);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
