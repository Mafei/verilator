// DESCRIPTION: A legal Active-region race with deterministic later NBA observation
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
`timescale 1ps/1ps
// verilog_format: off
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) $fatal(1, "check %0d line %0d got=%b expected=%b", checks, `__LINE__, (gotv), (expv)); end while (0)
`define STRINGIFY(x) `"x`"
// verilog_format: on
module t;
  event race;
  logic [6:0] active_value = '0;
  logic [6:0] nba_value = '0;
  logic [6:0] active_seen = '0;
  logic [6:0] nba_seen = '0;
  logic [6:0] payload = '0;
  int checks = 0;
  int phase;
  always @race begin
    active_value = payload;
  end
  always @race begin
    active_seen = active_value;
    nba_seen = nba_value;
  end
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, active_value, nba_value, active_seen, nba_seen, payload);
    for (phase = 0; phase < 4; phase++) begin
      #1;
      active_value = 7'h11;
      nba_value = 7'h22;
      payload = phase[0] ? 7'bz10x010 : 7'bx01z101;
      nba_value <= @race payload;
      #1;
      ->race;
      `checkh(nba_value, 7'h22);
      #1;
      // Ordering of independent Active processes is deliberately unrestricted.
      checks++;
      if ((active_seen !== 7'h11) && (active_seen !== payload))
        $fatal(1, "Active race produced a value outside its allowed set");
      `checkh(nba_seen, 7'h22);
      `checkh(active_value, payload);
      `checkh(nba_value, payload);
      $display("RACE phase=%0d active_seen=%b nba_seen=%b final=%b", phase, active_seen, nba_seen, nba_value);
    end
    $display("EVENT_NBA_RACE_PASS checks=%0d", checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
