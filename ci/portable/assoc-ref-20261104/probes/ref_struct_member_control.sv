// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Public control of a legal dynamic unpacked-struct member inout argument.
module ref_struct_member_control;
  typedef struct { int member; int untouched; } record_t;
  class Holder;
    record_t records[2];
  endclass
  record_t records[2];
  Holder holder;
  int index_value;
  int result;
  function automatic int bump(inout int value);
    int previous;
    previous = value;
    value = value + 1;
    return previous;
  endfunction
  initial begin
    if (!$value$plusargs("index=%d", index_value)) index_value = 1;
    holder = new;
    records[1] = '{7, 9};
    holder.records[1] = '{13, 17};
    result = bump(records[index_value].member);
    if (result !== 7 || records[1].member !== 8 || records[1].untouched !== 9) $fatal(1, "Struct member differs");
    result = bump(holder.records[index_value].member);
    if (result !== 13 || holder.records[1].member !== 14 || holder.records[1].untouched !== 17) $fatal(1, "Class struct member differs");
    $display("REF_STRUCT_MEMBER_PASS calls=2");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
