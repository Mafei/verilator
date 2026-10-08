// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  logic [7:0] mem[0:5];
  logic [511:0] packed_filename;
  logic [31:0] unknown_start = 32'h0000_000x;
  logic [31:0] unknown_end = 32'h0000_000z;
  bit [63:0] unsigned_overflow = 64'h8000_0000_0000_0000;
  localparam bit [511:0] KNOWN_FILENAME = "t/t_fourstate_readmem_h.mem";
  localparam logic [511:0] UNKNOWN_FILENAME = {8'hzz, "t/t_fourstate_readmem_h.mem"};
  bit [31:0] checks = 0;
  int which = 0;

  function automatic logic [7:0] sentinel(input int index);
    return (index % 2) != 0 ? 8'hz6 : 8'h5x;
  endfunction
  function automatic logic [7:0] loaded(input int index);
    case (index)
      1: return 8'h1x;
      2: return 8'hz5;
      3: return 8'haz;
      default: return 8'h3c;
    endcase
  endfunction
  task automatic reset_memory();
    for (int index = 0; index < 6; index++) mem[index] = sentinel(index);
  endtask
  task automatic check_word(input logic [7:0] value, input logic [7:0] expected);
    `checkh(value, expected);
    `checkh($isunknown(value), $isunknown(expected));
  endtask
  task automatic check_unchanged();
    for (int index = 0; index < 6; index++) check_word(mem[index], sentinel(index));
  endtask
  task automatic check_loaded();
    for (int index = 0; index < 6; index++)
      check_word(mem[index], index >= 1 && index <= 4 ? loaded(index) : sentinel(index));
  endtask

  initial begin
    if (!$value$plusargs("CASE=%d", which)) $fatal(1, "Missing CASE selection");
    reset_memory();
    case (which)
      0: $readmemb({`STRINGIFY(`TEST_OBJ_DIR), "/bad_0.mem"}, mem, 1, 4);
      1: $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_1.mem"}, mem, 1, 4);
      2: $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_2.mem"}, mem, 1, 4);
      // Bounded policy rejects >32-bit @ rather than adopting reference wraparound.
      3: $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_3.mem"}, mem, 1, 4);
      4: $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_4.mem"}, mem, 1, 4);
      5: $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_5.mem"}, mem, 1, 4);
      6: begin
        // Known packed literals, parameters and runtime-selected packed names.
        $readmemh({"t/", "t_fourstate_readmem_h.mem"}, mem, 1, 4);
        check_loaded();
        reset_memory();
        $readmemh(KNOWN_FILENAME, mem, 1, 4);
        check_loaded();
        reset_memory();
        packed_filename = "t/t_fourstate_readmem_h.mem";
        $readmemh(packed_filename, mem, 1, 4);
        check_loaded();
        reset_memory();

        // Deliberate local policy: any X/Z filename/bound bit warns and does not
        // write. This does not certify the IEEE unknown-value conversion rules.
        $readmemh({8'hxx, "t/t_fourstate_readmem_h.mem"}, mem, 1, 4);
        check_unchanged();
        $readmemh(UNKNOWN_FILENAME, mem, 1, 4);
        check_unchanged();
        packed_filename = "t/t_fourstate_readmem_h.mem";
        packed_filename[7:0] = 8'hxx;
        $readmemh(packed_filename, mem, 1, 4);
        check_unchanged();
        packed_filename = "t/t_fourstate_readmem_h.mem";
        packed_filename[511] = 1'bz;
        $readmemh(packed_filename, mem, 1, 4);
        check_unchanged();
        $readmemh("t/t_fourstate_readmem_h.mem", mem, unknown_start, 4);
        check_unchanged();
        $readmemh("t/t_fourstate_readmem_h.mem", mem, 1, unknown_end);
        check_unchanged();
        $readmemh("t/t_fourstate_readmem_h.mem", mem, unsigned_overflow, 4);
        check_unchanged();
        $readmemh("t/t_fourstate_readmem_h.mem", mem, -1, 4);
        check_unchanged();
        $readmemh("t/t_fourstate_readmem_h.mem", mem, 1, 6);
        check_unchanged();
        $readmemh("t/t_fourstate_readmem_missing.mem", mem, 1, 4);
        check_unchanged();
      end
      7: begin
        $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_7.mem"}, mem, 1, 4);
        check_loaded();
      end
      8: begin
        $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_8.mem"}, mem, 1, 4);
        for (int index = 0; index < 6; index++)
          check_word(mem[index], index == 1 ? 8'h1x : (index == 2 ? 8'hz5 : sentinel(index)));
      end
      9: begin
        $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/bad_9.mem"}, mem, 1, 1);
        for (int index = 0; index < 6; index++)
          check_word(mem[index], index == 1 ? 8'haz : sentinel(index));
      end
      10: begin
        $readmemb({`STRINGIFY(`TEST_OBJ_DIR), "/bad_10.mem"}, mem, 1, 1);
        for (int index = 0; index < 6; index++)
          check_word(mem[index], index == 1 ? 8'b1100_10xz : sentinel(index));
      end
      default: $fatal(1, "Bad CASE selection");
    endcase
    if (which < 6) $fatal(1, "Malformed readmem input unexpectedly returned");
    $display("Readmem diagnostic checks: %0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
