// DESCRIPTION: Verilator: Duplicate explicit external header port name
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// IEEE 1364-2005 12.3.2 restricts duplicate explicit external port definitions.
// SV-BC 2012 quotes the same module rule in 23.2.2.1:
// https://www.accellera.org/images/eda/sv-bc/11409.html
// The referenced rules distinguish this case from legal bare (a,a) references.
// No claim is made that the complete IEEE 1800-2023 edition was reviewed.
module named_dup(.same(a), .same(b), d);
  output wire a, b;
  input wire d;
  assign a = d;
  assign b = ~d;
endmodule
module t;
  wire a, b;
  named_dup u(a, b, 1'b0);
endmodule
