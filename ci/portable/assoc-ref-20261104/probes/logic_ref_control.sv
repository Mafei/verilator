// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Public isolation of a four-state inout argument outside a fixed array.
module logic_ref_control;
  logic [64:0] values[2];
  int index_value;
  int result;
  function automatic int touch(inout logic [64:0] value);
    bit was_default;
    was_default = (value === {65{1'bx}});
    $display("LOGIC_REF_DEFAULT value=%h was_default=%0d", value, was_default);
    value = 65'h1_0000_0000_0000_0001;
    return int'(was_default);
  endfunction
  initial begin
    if (!$value$plusargs("index=%d", index_value)) index_value = 2;
    values[0] = {1'bz, 32'ha5a5_5a5a, 32'h01x3_45z7};
    values[1] = 65'h1_0000_0000_0000_0055;
    for (int step = 0; step < 4; ++step) begin
      result = touch(values[index_value]);
      if (result !== 1) $fatal(1, "Out-of-range logic reference must read all X");
      if (values[0] !== {1'bz, 32'ha5a5_5a5a, 32'h01x3_45z7}) $fatal(1, "Element 0 changed");
      if (values[1] !== 65'h1_0000_0000_0000_0055) $fatal(1, "Element 1 changed");
    end
    $display("LOGIC_REF_DEFAULT_PASS calls=4");
    $display("*-* All Finished *-*");
    $finish;
  end
endmodule
