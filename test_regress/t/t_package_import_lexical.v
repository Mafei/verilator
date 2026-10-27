// DESCRIPTION: Verilator: Explicit variable import definition-site visibility
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkd(gotv,expv) do begin if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d:  got=%0d exp=%0d\n", `__FILE__,`__LINE__, (gotv), (expv)); `stop; end checks++; end while(0)
// verilog_format: on

package lexical_pkg;
  byte entries[0:2];
endpackage

byte entries[0:0];

module lexical_scope #(parameter int TAG = 0);
  int checks = 0;
  int count_before;
  int count_after;

  `define IMPORT_LEXICAL_FUNCTION before_f
  `include "t/t_package_import_lexical.vh"
  `undef IMPORT_LEXICAL_FUNCTION

  if (TAG >= 0) begin : before_g
    initial begin
      #1;
      `checkd($size(entries), 1);
    end
  end
  initial begin : before_b
    #1;
    `checkd($size(entries), 1);
  end
  initial begin
    count_before = 0;
    foreach (entries[i]) count_before++;
    #2;
    `checkd(count_before, 1);
    `checkd(count_after, 3);
    `checkd(before_f(), 1);
    `checkd(after_f(), 3);
    `checkd(forward_f(), 7);
    `checkd(later, 5);
    `checkd(checks, 10);
    $display("IMPORT_LEXICAL tag=%0d checks=%0d", TAG, checks);
  end

  import lexical_pkg::entries;
  import lexical_pkg::entries;

  `define IMPORT_LEXICAL_FUNCTION after_f
  `include "t/t_package_import_lexical.vh"
  `undef IMPORT_LEXICAL_FUNCTION

  if (TAG >= 0) begin : after_g
    initial begin
      #1;
      `checkd($size(entries), 3);
    end
  end
  initial begin : after_b
    #1;
    `checkd($size(entries), 3);
  end
  initial begin
    count_after = 0;
    foreach (entries[i]) count_after++;
  end
  function automatic int forward_f();
    return 7;
  endfunction
  int later = 5;
endmodule

module lexical_generate;
  int checks = 0;
  initial begin
    #1;
    `checkd($size(entries), 1);
    #1;
    `checkd(checks, 2);
    $display("IMPORT_LEXICAL generate checks=%0d", checks);
  end
  if (1) begin
    import lexical_pkg::entries;
    initial begin
      #1;
      `checkd($size(entries), 3);
    end
  end
endmodule

module t;
  lexical_scope #(.TAG(0)) a();
  lexical_scope #(.TAG(1)) b();
  lexical_generate c();
  initial begin
    #3;
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
