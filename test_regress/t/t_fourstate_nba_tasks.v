// DESCRIPTION: Concurrent delayed NBA snapshots in class tasks and module tasks
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps/1ps
// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on
module t;
  logic [32:0] bank[3:1];
  logic [32:0] plain[3:1];
  wire [32:0] bank1 = bank[1];
  wire [32:0] bank2 = bank[2];
  wire [32:0] bank3 = bank[3];
  wire [32:0] plain1 = plain[1];
  wire [32:0] plain2 = plain[2];
  wire [32:0] plain3 = plain[3];
  class Writer;
    task schedule(input int index, input logic [32:0] data);
      t.bank[index] <= #2 data;
    endtask
  endclass
  Writer writer;
  logic [32:0] rhs;
  int checks = 0;
  int phase;
  int index;
  function automatic logic [32:0] payload(input int value);
    for (int bitno = 0; bitno < 33; bitno++) begin
      case ((value + bitno) % 4)
        0: payload[bitno] = 1'b0;
        1: payload[bitno] = 1'b1;
        2: payload[bitno] = 1'bx;
        3: payload[bitno] = 1'bz;
      endcase
    end
  endfunction
  task automatic schedule_plain(input int target, input logic [32:0] data);
    plain[target] <= #2 data;
  endtask
  initial begin
    writer = new;
    foreach (bank[slot]) begin bank[slot] = '0; plain[slot] = '0; end
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, bank1, bank2, bank3, plain1, plain2, plain3);
    for (phase = 0; phase < 3; phase++) begin
      #1;
      for (index = 1; index <= 3; index++) begin
        rhs = payload(phase + index);
        writer.schedule(index, rhs);
        schedule_plain(index, rhs);
      end
      rhs = payload(phase + 3);
      index = 3;
      #1;
      for (index = 1; index <= 3; index++) begin
        `checkh(bank[index], phase == 0 ? 33'b0 : payload(phase + index - 1));
        `checkh(plain[index], phase == 0 ? 33'b0 : payload(phase + index - 1));
      end
      #2;
      for (index = 1; index <= 3; index++) begin
        `checkh(bank[index], payload(phase + index));
        `checkh(plain[index], payload(phase + index));
      end
      $display("TASK_FINAL phase=%0d bank1=%b bank2=%b bank3=%b", phase, bank1, bank2, bank3);
    end
    $display("EVENT_NBA_TASKS_PASS checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
