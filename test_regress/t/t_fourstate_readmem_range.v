// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module t;
  logic [7:0] asc[2:5];
  logic [7:0] desc[5:2];
  logic [7:0] negasc[-2:1];
  logic [7:0] negdesc[1:-2];
  logic [7:0] standard[0:5];
  bit [31:0] checks = 0;

  function automatic logic [7:0] word(input int index);
    case (index)
      0: return 8'h1x;
      1: return 8'hz5;
      2: return 8'haz;
      default: return 8'h3c;
    endcase
  endfunction
  function automatic logic [7:0] sentinel(input int index);
    return (index % 2) != 0 ? 8'hz6 : 8'h5x;
  endfunction
  task automatic reset_arrays();
    for (int index = 2; index <= 5; index++) begin
      asc[index] = sentinel(index);
      desc[index] = sentinel(index);
    end
    for (int index = -2; index <= 1; index++) begin
      negasc[index] = sentinel(index);
      negdesc[index] = sentinel(index);
    end
    for (int index = 0; index <= 5; index++) standard[index] = sentinel(index);
  endtask
  task automatic check_word(input logic [7:0] value, input logic [7:0] expected);
    `checkh(value, expected);
    // Scalar snapshots avoid reference-simulator $isunknown(mem[index]) quirks.
    `checkh($isunknown(value), $isunknown(expected));
  endtask

  initial begin
    reset_arrays();
    // Default traverses lowest to highest address, independent of declaration order.
    $readmemh("t/t_fourstate_readmem_h.mem", asc);
    $readmemb("t/t_fourstate_readmem_b.mem", desc);
    $readmemh("t/t_fourstate_readmem_h.mem", negasc);
    $readmemb("t/t_fourstate_readmem_b.mem", negdesc);
    for (int index = 2; index <= 5; index++) begin
      check_word(asc[index], word(index - 2));
      check_word(desc[index], word(index - 2));
    end
    for (int index = -2; index <= 1; index++) begin
      check_word(negasc[index], word(index + 2));
      check_word(negdesc[index], word(index + 2));
    end
    reset_arrays();
    // Start-only ends at the highest declared address, not the rightmost bound.
    $readmemh("t/t_fourstate_readmem_2h.mem", asc, 4);
    $readmemb("t/t_fourstate_readmem_2b.mem", desc, 4);
    for (int index = 2; index <= 5; index++) begin
      check_word(asc[index], index < 4 ? sentinel(index) : (index == 4 ? 8'he1 : 8'hd2));
      check_word(desc[index], index < 4 ? sentinel(index) : (index == 4 ? 8'he1 : 8'hd2));
    end
    reset_arrays();
    $readmemh("t/t_fourstate_readmem_h.mem", standard, 1, 4);
    for (int index = 0; index <= 5; index++)
      check_word(standard[index], index >= 1 && index <= 4 ? word(index - 1) : sentinel(index));
    reset_arrays();
    $readmemb("t/t_fourstate_readmem_b.mem", standard, 1, 4);
    for (int index = 0; index <= 5; index++)
      check_word(standard[index], index >= 1 && index <= 4 ? word(index - 1) : sentinel(index));
    reset_arrays();
    // Explicit start > end reverses traversal for either declaration direction.
    $readmemh("t/t_fourstate_readmem_h.mem", asc, 5, 2);
    $readmemb("t/t_fourstate_readmem_b.mem", desc, 5, 2);
    $readmemh("t/t_fourstate_readmem_h.mem", negasc, 1, -2);
    $readmemb("t/t_fourstate_readmem_b.mem", negdesc, 1, -2);
    for (int index = 2; index <= 5; index++) begin
      check_word(asc[index], word(5 - index));
      check_word(desc[index], word(5 - index));
    end
    for (int index = -2; index <= 1; index++) begin
      check_word(negasc[index], word(1 - index));
      check_word(negdesc[index], word(1 - index));
    end
    reset_arrays();
    // Sparse jumps are absolute addresses; untouched holes retain both halves.
    $readmemh("t/t_fourstate_readmem_sparse_h.mem", asc, 2, 5);
    $readmemb("t/t_fourstate_readmem_sparse_b.mem", desc, 2, 5);
    for (int index = 2; index <= 5; index++) begin
      check_word(asc[index], index == 2 ? 8'h1x : (index == 4 ? 8'hz5 : sentinel(index)));
      check_word(desc[index], index == 2 ? 8'h1x : (index == 4 ? 8'hz5 : sentinel(index)));
    end
    reset_arrays();
    $readmemh("t/t_fourstate_readmem_reverse_h.mem", asc, 5, 2);
    $readmemb("t/t_fourstate_readmem_reverse_b.mem", desc, 5, 2);
    for (int index = 2; index <= 5; index++) begin
      check_word(asc[index], index == 5 ? 8'h1x : (index == 3 ? 8'hz5 : sentinel(index)));
      check_word(desc[index], index == 5 ? 8'h1x : (index == 3 ? 8'hz5 : sentinel(index)));
    end
    reset_arrays();
    // Reference-verified signed 32-bit @ encodings for -2 and zero.
    $readmemh("t/t_fourstate_readmem_negative_h.mem", negasc, -2, 1);
    $readmemb("t/t_fourstate_readmem_negative_b.mem", negdesc, -2, 1);
    for (int index = -2; index <= 1; index++) begin
      check_word(negasc[index], index == -2 ? 8'h1x : (index == 0 ? 8'hz5 : sentinel(index)));
      check_word(negdesc[index], index == -2 ? 8'h1x : (index == 0 ? 8'hz5 : sentinel(index)));
    end
    $display("Readmem range checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
