// DESCRIPTION: Verilator: Clipped event-controlled NBA array writes
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [3:0] done;
  wire [31:0] total_checks = w4.checks + w63.checks + w65.checks + w95.checks;
  clipped_width #(4) w4(done[0]);
  clipped_width #(63) w63(done[1]);
  clipped_width #(65) w65(done[2]);
  clipped_width #(95) w95(done[3]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, w4.bank0_view, w4.bank1_view, w63.bank0_view, w63.bank1_view,
              w65.bank0_view, w65.bank1_view, w95.bank0_view, w95.bank1_view);
    wait (done === '1);
    #1;
    $display("Clipped NBA checks: %0d", total_checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module clipped_width #(parameter int WIDTH = 4)(output bit done = 0);
`ifdef PARTSELECT_FOURSTATE
  logic [WIDTH-1:0] bank[0:1];
`else
  bit [WIDTH-1:0] bank[0:1];
`endif
  wire [WIDTH-1:0] bank0_view = bank[0];
  wire [WIDTH-1:0] bank1_view = bank[1];
  int unsigned checks = 0;
  int round;
  int kind;
  int target;
  int base;
  int selection_lsb;
  int selection_width;
  logic [96:0] payload;
  logic [WIDTH-1:0] old0;
  logic [WIDTH-1:0] old1;
  logic [WIDTH-1:0] expected;
  event update_event;

  function automatic logic [96:0] make_pattern;
    for (int bitno = 0; bitno < 97; bitno++) begin
`ifdef PARTSELECT_FOURSTATE
      case (bitno % 4)
        0: make_pattern[bitno] = 1'b0;
        1: make_pattern[bitno] = 1'b1;
        2: make_pattern[bitno] = 1'bx;
        default: make_pattern[bitno] = 1'bz;
      endcase
`else
      make_pattern[bitno] = (bitno % 3) == 1;
`endif
    end
  endfunction

  localparam logic [96:0] PATTERN = make_pattern();
  localparam logic [WIDTH+1:0] BOTH_PAYLOAD = PATTERN[WIDTH+1:0];
`ifdef PARTSELECT_FOURSTATE
  localparam logic [1:0] LOW_PAYLOAD = 2'bz1;
  localparam logic [1:0] HIGH_PAYLOAD = 2'b1x;
  localparam logic [1:0] VALID_PAYLOAD = 2'bxz;
`else
  localparam logic [1:0] LOW_PAYLOAD = 2'b10;
  localparam logic [1:0] HIGH_PAYLOAD = 2'b01;
  localparam logic [1:0] VALID_PAYLOAD = 2'b10;
`endif

  // Calculate the oracle one destination bit at a time, without shifts or masks.
  task automatic prepare_case;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      old0[bitno] = ((bitno + round + kind) % 3) == 1;
      old1[bitno] = ~old0[bitno];
    end
    bank[0] = old0;
    bank[1] = old1;
    target = 0;
    case (kind)
      0: begin selection_lsb = -1; selection_width = 2; payload = 97'(LOW_PAYLOAD); end
      1: begin selection_lsb = WIDTH - 1; selection_width = 2; payload = 97'(HIGH_PAYLOAD); end
      2: begin selection_lsb = -2; selection_width = 2; payload = 97'(2'b11); end
      3: begin selection_lsb = WIDTH; selection_width = 2; payload = 97'(2'b11); end
      4: begin selection_lsb = -1; selection_width = WIDTH + 2; payload = 97'(BOTH_PAYLOAD); end
      5: begin selection_lsb = 1; selection_width = 2; payload = 97'(VALID_PAYLOAD); end
      6: begin selection_lsb = -1; selection_width = 6; payload = PATTERN; end
      7: begin selection_lsb = WIDTH > 4 ? 31 : 1; selection_width = 33; payload = PATTERN; end
      8: begin selection_lsb = WIDTH + 1; selection_width = 2; payload = PATTERN; end
    endcase
    base = selection_lsb;
    expected = old0;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      if ((bitno >= selection_lsb) && (bitno < selection_lsb + selection_width))
        expected[bitno] = payload[bitno - selection_lsb];
    end
  endtask

  initial begin
    for (round = 0; round < 2; round++) begin
      for (kind = 0; kind < 9; kind++) begin
        prepare_case();
        // These intentional partial/out-of-range selects exercise clipping, not diagnostics.
        // verilator lint_off SELRANGE
        case (kind)
          0: bank[target][0:-1] <= @update_event LOW_PAYLOAD;
          1: bank[target][WIDTH:WIDTH-1] <= @update_event HIGH_PAYLOAD;
          2: bank[target][-1:-2] <= @update_event 2'b11;
          3: bank[target][WIDTH+1:WIDTH] <= @update_event 2'b11;
          4: bank[target][WIDTH:-1] <= @update_event BOTH_PAYLOAD;
          5: bank[target][2:1] <= @update_event VALID_PAYLOAD;
          6: bank[target][base+:6] <= @update_event payload[5:0];
          7: bank[target][base+:33] <= @update_event payload[32:0];
          8: bank[target][base+:2] <= @update_event payload[1:0];
        endcase
        // verilator lint_on SELRANGE
        // All target, select and RHS values must be saved by the issuing process.
        target = 1;
        base = WIDTH + 10;
        payload = 0;
        `checkh(bank[0], old0);
        `checkh(bank[1], old1);
        #1;
        ->update_event;
        `checkh(bank[0], old0);
        `checkh(bank[1], old1);
        #0;
        `checkh(bank[0], old0);
        `checkh(bank[1], old1);
        $strobe("CLIP STROBE width=%0d round=%0d case=%0d t=%0t bank0=%b bank1=%b",
                WIDTH, round, kind, $time, bank0_view, bank1_view);
        #1;
        `checkh(bank[0], expected);
        `checkh(bank[1], old1);
        #1;
      end
    end
    done = 1;
  end
endmodule
