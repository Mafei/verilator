// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

module t;
  localparam VALUE = 7;
  integer cell;
  integer config;
  integer design;
  integer endconfig;
  integer incdir;
  integer include;
  integer instance;
  integer liblist;
  integer library;
  integer use;

  `begin_keywords "1364-2001"
  integer bit;
  `end_keywords

  initial begin
    cell = VALUE;
    config = cell;
    design = config;
    endconfig = design;
    incdir = endconfig;
    include = incdir;
    instance = include;
    liblist = instance;
    library = liblist;
    use = library;
    bit = use;
    $finish;
  end
endmodule
