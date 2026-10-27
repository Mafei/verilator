// DESCRIPTION: Verilator: Conditional code motion across aliased class members
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

class member_state;
  bit [7:0] data;
  bit flag;
  bit ready;
  int calls = 0;
  function member_state receiver;
    calls++;
    return this;
  endfunction
endclass

module t;
  initial begin
    static member_state original = new;
    static member_state alias_handle;
    bit condition;
    static bit wrongly_merged = 0;
    alias_handle = original.receiver();
    condition = $c("1");
    if (condition) alias_handle.data = 8'h35;
    if (original.data !== 8'h35) $fatal(1, "Member write moved across an aliased read");
    if (original.flag !== 1'b0) $fatal(1, "Member write moved before an aliased read");
    if (condition) alias_handle.flag = 1;
    if (original.flag !== 1'b1) $fatal(1, "Second member write lost");
    if (original.calls !== 1) $fatal(1, "Receiver was evaluated more than once");

    // The first statement changes the member used by both conditions.
    original.ready = 1;
    if (original.ready) alias_handle.ready = 0;
    if (original.ready) wrongly_merged = 1;
    if (original.ready !== 1'b0) $fatal(1, "Condition member write lost");
    if (wrongly_merged !== 1'b0) $fatal(1, "Member condition was reused after a write");
    $display("Aliased member checks: 6");
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
