// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

module child(input logic [6:0] drive, output wire [6:0] result);
  assign result = drive;
endmodule

module child_bit(input bit [6:0] drive, output bit [6:0] result);
  assign result = drive;
endmodule

module t;
  typedef bit [6:0] bitword_t;
  logic [6:0] drive;
  logic [6:0] memory [3:1];
  logic [6:0] fixed_memory [0:0];
  logic [6:0] bit_memory [0:0];
  logic [20:0] word;
  int index;
  bit [31:0] first;

  function automatic bit [31:0] selected_bit();
    $display("selected_bit=%0d", first);
    return first;
  endfunction

  child h_memory(drive, memory[index]);
  child h_fixed(drive, fixed_memory[0]);
  child_bit h_bit(bitword_t'(drive), bit_memory[0]);
  child h_word(drive, word[selected_bit() +: 7]);

  initial begin
    index = 1;
    first = 0;
    drive = 7'b10xz010;
    #1;
    `checkh(memory[1], 7'b10xz010);
    `checkh(fixed_memory[0], 7'b10xz010);
    `checkh(bit_memory[0], 7'b1000010);
    `checkh(word[6:0], 7'b10xz010);
    // Changing only the output selections must update the newly selected variables.
    index = 2;
    first = 7;
    #1;
    `checkh(memory[2], 7'b10xz010);
    `checkh(word[13:7], 7'b10xz010);
    `checkh(memory[1], 7'b10xz010);
    `checkh(word[6:0], 7'b10xz010);
    for (int i = 1; i <= 3; i++) begin
      index = i;
      first = 32'((i - 1) * 7);
      drive = 7'(i);
      #1;
      `checkh(memory[i], 7'(i));
      `checkh(fixed_memory[0], 7'(i));
      `checkh(bit_memory[0], 7'(i));
      `checkh(word[first +: 7], 7'(i));
      if (i > 1) begin
        `checkh(memory[i - 1], 7'(i - 1));
        `checkh(word[(i - 2) * 7 +: 7], 7'(i - 1));
      end
    end
    drive = 'x;
    #1;
    `checkh(memory[3], 7'bxxxxxxx);
    `checkh(fixed_memory[0], 7'bxxxxxxx);
    `checkh(bit_memory[0], 7'b0000000);
    `checkh(word[20:14], 7'bxxxxxxx);
    drive = 'z;
    #1;
    `checkh(memory[3], 7'bzzzzzzz);
    `checkh(fixed_memory[0], 7'bzzzzzzz);
    `checkh(bit_memory[0], 7'b0000000);
    `checkh(word[20:14], 7'bzzzzzzz);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
