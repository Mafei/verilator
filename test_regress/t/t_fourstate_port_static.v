// DESCRIPTION: Verilator: Static timed subroutine input storage remains a variable
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [3:0] done;
  wire [31:0] total_checks = w7.checks + w33.checks + w65.checks + w95.checks;
  port_static_case #(7) w7 (done[0]);
  port_static_case #(33) w33 (done[1]);
  port_static_case #(65) w65 (done[2]);
  port_static_case #(95) w95 (done[3]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done === 4'b1111);
    #1ps;
    $display("Static port storage checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module port_static_case #(parameter int WIDTH = 7) (output bit done = 0);
  logic [WIDTH-1:0] data = '0;
  wire [WIDTH-1:0] static_value = receive.value;
  int unsigned checks = 0;

  task static receive(input logic [WIDTH-1:0] value);
    #1;
  endtask

  initial begin
    #1;
    `checkh(static_value, {WIDTH{1'bx}});
    for (int phase = 0; phase < 5; ++phase) begin
      for (int index = 0; index < WIDTH; ++index) begin
        case (phase)
          0: begin
            case (index % 4)
              0: data[index] = 1'b0;
              1: data[index] = 1'b1;
              2: data[index] = 1'bx;
              3: data[index] = 1'bz;
            endcase
          end
          1: data[index] = (index % 3 == 1);
          2: data[index] = 1'bz;
          3: data[index] = 1'bx;
          4: data[index] = (index % 3 != 1);
        endcase
      end
      #1;
      receive(data);
      `checkh(static_value, data);
    end
    done = 1;
  end
endmodule
