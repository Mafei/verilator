// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
// Bounded runtime compatibility probe; no timing or simulator coverage claim.
module runtime_cxx14;
   typedef bit [94:0] bits95_t;
   logic [94:0] value95;
   logic [94:0] copied95;
   logic [95:0] signed96;
   bits95_t clean95;
   int signed cast32;
   int unsigned index;

   initial begin
`ifdef VERILATOR
      $c("static_assert(__cplusplus == 201402L, \"C++14 runtime required\");");
      index = $c("0U");
`else
      index = 0;
`endif
      value95 = '1;
      value95[index +: 2] = 2'bxz;
      copied95 = value95;
      if (copied95 !== {{93{1'b1}}, 2'bxz}) $fatal(1, "CXX14_WIDE_COPY_FAILED");
      if ((&copied95) !== 1'bx || (|copied95) !== 1'b1 || (^copied95) !== 1'bx)
        $fatal(1, "CXX14_REDUCTION_FAILED");
      clean95 = bits95_t'(copied95);
      if (clean95 !== {{93{1'b1}}, 2'b00}) $fatal(1, "CXX14_TWO_STATE_CAST_FAILED");
      // int is two-state: unknown and high-impedance bits convert to zero.
      cast32 = int'(copied95);
      if (cast32 !== {{30{1'b1}}, 2'b00}) $fatal(1, "CXX14_INT_CAST_FAILED");
      signed96 = 96'($signed(copied95));
      if (signed96 !== {{94{1'b1}}, 2'bxz}) $fatal(1, "CXX14_SIGNED_CAST_FAILED");
      $display("CXX14_NO_TIMING_FOURSTATE_RUNTIME_PASS");
      $finish;
   end
endmodule
