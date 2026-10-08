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
  logic [6:0] memory [3:1];
  logic [2:0] index;
  logic [6:0] data;
  logic [6:0] zero_memory [0:3];
  logic [1:0] zero_index;

  initial begin
    memory[1] = 7'h11;
    memory[2] = 7'h22;
    memory[3] = 7'h33;
    for (int i = 0; i < 4; i++) zero_memory[i] = 7'(i + 10);
    #1;
    index = 3'bxxx;
    data = memory[index];
    `checkh(data, 7'bxxxxxxx);
    memory[index] = 7'h7f;
    #1;
    `checkh(memory[1], 7'h11);
    `checkh(memory[2], 7'h22);
    `checkh(memory[3], 7'h33);

    // A zero-based array exposes accidental X/Z-to-zero index conversion.
    zero_index = 2'bxz;
    data = zero_memory[zero_index];
    `checkh(data, 7'bxxxxxxx);
    zero_memory[zero_index] <= 7'h7f;
    #1;
    for (int i = 0; i < 4; i++) `checkh(zero_memory[i], 7'(i + 10));

    index = 3'd2;
    memory[index] <= 7'b10xz010;
    index = 3'd1;
    #1;
    `checkh(memory[2], 7'b10xz010);
    `checkh(memory[1], 7'h11);
    index = 3'd0;
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
