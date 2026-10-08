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
  wire [12:0] done;
  wire observer_done;
  readmem_observe observer(observer_done);
  readmem_check #(1) m1(done[0]);
  readmem_check #(7) m7(done[1]);
  readmem_check #(8) m8(done[2]);
  readmem_check #(9) m9(done[3]);
  readmem_check #(16) m16(done[4]);
  readmem_check #(17) m17(done[5]);
  readmem_check #(32) m32(done[6]);
  readmem_check #(33) m33(done[7]);
  readmem_check #(64) m64(done[8]);
  readmem_check #(65) m65(done[9]);
  readmem_check #(95) m95(done[10]);
  readmem_check #(128) m128(done[11]);
  readmem_check #(176) m176(done[12]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, m8.probe_h, m8.probe_b, m8.probe_h_z, m8.probe_b_z);
    #10;
    if (done !== '1) $fatal(1, "readmem checks did not finish");
    if (observer_done !== 1'b1) $fatal(1, "readmem observer did not finish");
    $display("Readmem width checks: %0d", m1.checks + m7.checks + m8.checks + m9.checks
             + m16.checks + m17.checks + m32.checks + m33.checks + m64.checks + m65.checks
             + m95.checks + m128.checks + m176.checks);
    $display("Readmem observer checks: %0d", observer.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module readmem_observe(output bit done = 0);
  logic mem[0:0];
  logic mirror;
  bit [31:0] checks = 0;

  // Observe from a separate process: the readmem write must schedule readers of
  // both encoded halves, including mask-only X->1 and value-only X->Z updates.
  always_comb mirror = mem[0];

  task automatic check_mirror(input logic wanted);
    `checkh(mirror, wanted);
    `checkh($isunknown(mirror), $isunknown(wanted));
  endtask

  initial begin
    #1;
    check_mirror(1'bx);
    $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/short_h1.mem"}, mem);
    #1;
    check_mirror(1'b1);
    $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/short_x_h1.mem"}, mem);
    #1;
    check_mirror(1'bx);
    $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/short_z_h1.mem"}, mem);
    #1;
    check_mirror(1'bz);
    $readmemh({`STRINGIFY(`TEST_OBJ_DIR), "/short_h1.mem"}, mem);
    #1;
    check_mirror(1'b1);
    done = 1;
  end
endmodule

module readmem_check #(parameter WIDTH = 8) (output bit done = 0);
  typedef logic [WIDTH-1:0] word_t;
  word_t h[0:5];
  logic [WIDTH-1:0] b[0:5];
  logic signed [WIDTH-1:0] sh[0:5];
  logic signed [WIDTH-1:0] sb[0:5];
  logic [WIDTH-1:0] probe_h, probe_b, probe_h_z, probe_b_z;
  bit [31:0] checks = 0;
  bit [31:0] filename_calls = 0;
  bit [31:0] start_calls = 0;
  bit [31:0] end_calls = 0;

  function automatic string path(input string stem, input bit binary);
    filename_calls++;
    return $sformatf("%s/%s_%s%0d.mem", `STRINGIFY(`TEST_OBJ_DIR), stem,
                     binary ? "b" : "h", WIDTH);
  endfunction
  function automatic int first_addr();
    start_calls++;
    return 1;
  endfunction
  function automatic int last_addr();
    end_calls++;
    return 4;
  endfunction

  function automatic logic [WIDTH-1:0] expected(input bit binary, input int kind);
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      case (kind)
        0: expected[bitno] = 1'b0;
        1: expected[bitno] = (bitno % 3) == 1;
        4: expected[bitno] = (bitno % 3) != 1;
        2, 3: begin
          if (binary) begin
            case (bitno % 4)
              0: expected[bitno] = kind == 2 ? 1'bx : 1'bz;
              1: expected[bitno] = kind == 2 ? 1'bz : 1'bx;
              2: expected[bitno] = kind == 2;
              3: expected[bitno] = kind == 3;
            endcase
          end else begin
            case ((bitno / 4) % 4)
              0: expected[bitno] = kind == 2 ? 1'bx : 1'bz;
              1: expected[bitno] = kind == 2 ? 1'bz : 1'bx;
              2: expected[bitno] = (bitno % 2) == (kind == 2 ? 0 : 1);
              3: expected[bitno] = (bitno % 2) == (kind == 2 ? 1 : 0);
            endcase
          end
        end
        5: expected[bitno] = bitno == 0;
        6: expected[bitno] = bitno < (binary ? 1 : 4) ? 1'bx : 1'b0;
        7: expected[bitno] = bitno < (binary ? 1 : 4) ? 1'bz : 1'b0;
        default: expected[bitno] = 1'bx;
      endcase
    end
  endfunction

  task automatic check_word(input logic [WIDTH-1:0] value,
                            input logic [WIDTH-1:0] wanted);
    // Snapshot arguments before $isunknown; this also avoids Icarus array-index
    // evaluation quirks. Case equality independently verifies distinct X/Z.
    `checkh(value, wanted);
    `checkh($isunknown(value), $isunknown(wanted));
  endtask

  task automatic check_arrays(input int phase);
    logic [WIDTH-1:0] eh, eb;
    for (int index = 0; index < 6; index++) begin
      eh = 'x;
      eb = 'x;
      if (index >= 1 && index <= 4) begin
        eh = expected(0, index - 1);
        eb = expected(1, index - 1);
        if (phase >= 1 && index == 2) begin
          eh = expected(0, 4);
          eb = expected(1, 4);
        end
        if (phase >= 1 && index == 3) begin
          eh = expected(0, 1);
          eb = expected(1, 1);
        end
        if (phase >= 2 && index == 1) begin
          eh = expected(0, 2);
          eb = expected(1, 2);
        end
        if (phase == 3 && index == 4) begin
          eh = expected(0, 5);
          eb = expected(1, 5);
        end
        if (phase == 4 && index >= 3) begin
          eh = expected(0, index == 3 ? 6 : 7);
          eb = expected(1, index == 3 ? 6 : 7);
        end
      end
      check_word(h[index], eh);
      check_word(b[index], eb);
      check_word(sh[index], eh);
      check_word(sb[index], eb);
    end
    probe_h = h[3];
    probe_b = b[3];
    probe_h_z = h[4];
    probe_b_z = b[4];
  endtask

  initial begin
    for (int index = 0; index < 6; index++) begin
      `checkh(h[index], {WIDTH{1'bx}});
      `checkh(b[index], {WIDTH{1'bx}});
      `checkh(sh[index], {WIDTH{1'bx}});
      `checkh(sb[index], {WIDTH{1'bx}});
    end
    #1;
    $readmemh(path("mixed", 0), h, first_addr(), last_addr());
    $readmemb(path("mixed", 1), b, first_addr(), last_addr());
    $readmemh(path("mixed", 0), sh, first_addr(), last_addr());
    $readmemb(path("mixed", 1), sb, first_addr(), last_addr());
    `checkh(filename_calls, 4);
    `checkh(start_calls, 4);
    `checkh(end_calls, 4);
    check_arrays(0);
    #1;
    $readmemh(path("known", 0), h, 2, 3);
    $readmemb(path("known", 1), b, 2, 3);
    $readmemh(path("known", 0), sh, 2, 3);
    $readmemb(path("known", 1), sb, 2, 3);
    check_arrays(1);
    #1;
    $readmemh(path("sparse", 0), h, 1, 4);
    $readmemb(path("sparse", 1), b, 1, 4);
    $readmemh(path("sparse", 0), sh, 1, 4);
    $readmemb(path("sparse", 1), sb, 1, 4);
    check_arrays(2);
    #1;
    $readmemh(path("short", 0), h, 4, 4);
    $readmemb(path("short", 1), b, 4, 4);
    $readmemh(path("short", 0), sh, 4, 4);
    $readmemb(path("short", 1), sb, 4, 4);
    check_arrays(3);
    #1;
    $readmemh(path("short_x", 0), h, 3, 3);
    $readmemb(path("short_x", 1), b, 3, 3);
    $readmemh(path("short_x", 0), sh, 3, 3);
    $readmemb(path("short_x", 1), sb, 3, 3);
    $readmemh(path("short_z", 0), h, 4, 4);
    $readmemb(path("short_z", 1), b, 4, 4);
    $readmemh(path("short_z", 0), sh, 4, 4);
    $readmemb(path("short_z", 1), sb, 4, 4);
    check_arrays(4);
    `checkh(filename_calls, 24);
    `checkh(start_calls, 4);
    `checkh(end_calls, 4);
    done = 1;
  end
endmodule
