// DESCRIPTION: Split array-index bounds proof for an ascending 33-bit word
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
// verilog_format: off
`define STRINGIFY_(x) `"x`"
`define STRINGIFY(x) `STRINGIFY_(x)
// verilog_format: on
`ifndef TEST_DUMPFILE
`define TEST_DUMPFILE t_fourstate_array_guard.vcd
`endif
`timescale 1ps / 1ps
module lane (
    output bit done
);
  /* verilator lint_off ASCRANGE */
  logic [0:32] bank[-2:0];
  /* verilator lint_on ASCRANGE */
  int side_effects;
  int checks;
  initial begin
    done = 0;
    side_effects = 0;
    checks = 0;
    bank[-2] = 33'h11;
    bank[-1] = 33'h22;
    bank[0] = 33'h33;
    #1;
    $display("ARRAY_GUARD first=%b middle=%b last=%b", bank[-2], bank[-1], bank[0]);
    if (bank[-2] !== 33'h11 || bank[-1] !== 33'h22 || bank[0] !== 33'h33)
      $fatal(1, "Known initialization corrupted value/XZ planes");
    done = 1;
  end
endmodule
module t;
  bit done;
  lane u (done);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    wait (done);
    $display("ARRAY_GUARD_PASS");
    $finish;
  end
endmodule
