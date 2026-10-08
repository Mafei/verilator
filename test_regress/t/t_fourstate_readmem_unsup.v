// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  logic [7:0] mem[0:1];
  logic [7:0] multidim[0:1][0:1];
  logic [1:0][3:0] packed_multidim[0:1];
  typedef struct packed {
    logic [3:0] upper;
    logic [3:0] lower;
  } packed_word_t;
  packed_word_t structs[0:1];
  logic [7:0] forced[0:1] /* verilator forceable */;
  bit [64:0] wide_address = 65'h1_0000_0000_0000_0000;
  wire [7:0] port_memory[0:1];
  readmem_port port_check(port_memory);

  task automatic automatic_storage();
    logic [7:0] local_mem[0:1];
    $readmemh("t/t_fourstate_readmem_2h.mem", local_mem);
  endtask

  initial begin
    $readmemh("t/t_fourstate_readmem_2h.mem", mem, wide_address, 1);
    $readmemh("t/t_fourstate_readmem_2h.mem", multidim);
    $readmemh("t/t_fourstate_readmem_2h.mem", packed_multidim);
    $readmemh("t/t_fourstate_readmem_2h.mem", structs);
    $readmemh("t/t_fourstate_readmem_2h.mem", forced);
    automatic_storage();
  end
endmodule

module readmem_port(output logic [7:0] mem[0:1]);
  initial $readmemh("t/t_fourstate_readmem_2h.mem", mem);
endmodule
