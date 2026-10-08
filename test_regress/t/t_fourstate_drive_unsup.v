// DESCRIPTION: Verilator: Bounded four-state drive contexts
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`ifdef DRIVE_CASE_8
package drive_pkg;
  reg package_q;
endpackage
`endif

module t;
  reg data = 0;
  reg enable = 0;
  wire result;
  reg q = 0;
`ifdef DRIVE_CASE_1
  bufif1 (strong1, weak0) b (result, data, enable);
`elsif DRIVE_CASE_2
  bufif1 #(2) b (result, data, enable);
`elsif DRIVE_CASE_3
  nmos b (result, data, enable);
`elsif DRIVE_CASE_4
  pmos b (result, 1'bz, 1'b0);
`elsif DRIVE_CASE_5
  bufif1 b (result, data, enable);
  assign result = q;
`elsif DRIVE_CASE_6
  bufif0 b (result, 1'b1, 1'bx);
  assign result = 1'b0;
`elsif DRIVE_CASE_7
  initial assign q = data | enable;
`elsif DRIVE_CASE_8
  import drive_pkg::package_q;
  initial deassign package_q;
`elsif DRIVE_CASE_9
  drive_child u ();
  initial deassign u.q;
`elsif DRIVE_CASE_10
  initial begin
    force q = data;
    release q;
    deassign q;
  end
`elsif DRIVE_CASE_11
  reg public_q  /* verilator public_flat_rw */;
  initial deassign public_q;
`elsif DRIVE_CASE_14
  reg [6:0] partial_q;
  initial partial_q[3:0] = #1 4'bxxzz;
`elsif DRIVE_CASE_15
  task automatic delayed_local;
    reg local_q;
    local_q = #1 data;
  endtask
  initial delayed_local();
`elsif DRIVE_CASE_16
  drive_child u ();
  initial u.q = #1 data;
`elsif DRIVE_CASE_17
  initial begin
    force q = data;
    release q;
    q = #1 enable;
  end
`endif
endmodule

`ifdef DRIVE_CASE_9
`define DRIVE_CHILD
`elsif DRIVE_CASE_16
`define DRIVE_CHILD
`endif
`ifdef DRIVE_CHILD
module drive_child;
  reg q = 0;
endmodule
`undef DRIVE_CHILD
`endif

`ifdef DRIVE_CASE_12
module drive_input (
    input wire pin,
    input wire data,
    input wire enable
);
  bufif1 b (pin, data, enable);
endmodule
`endif

`ifdef DRIVE_CASE_13
module drive_inout (
    inout wire pin,
    input wire data,
    input wire enable
);
  bufif1 b (pin, data, enable);
endmodule
`endif
