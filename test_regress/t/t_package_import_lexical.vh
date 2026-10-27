// DESCRIPTION: Verilator: Repeated include at distinct lexical import views
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

function automatic int `IMPORT_LEXICAL_FUNCTION();
  return $size(entries);
endfunction
