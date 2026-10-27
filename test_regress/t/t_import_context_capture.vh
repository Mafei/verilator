// DESCRIPTION: Verilator: Repeated source with distinct expansion sites.
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Intentionally no include guard: both functions have the same source coordinates.
// verilog_format: off
`line 1 "capture_expansion.sv" 0
  function automatic int `CAP_FUNCTION();
    return $size(entries);
  endfunction
// verilog_format: on
