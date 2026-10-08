// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps/1ps

// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [4:0] done;
  vector_check #(7) w7(done[0]);
  vector_check #(33) w33(done[1]);
  vector_check #(65) w65(done[2]);
  vector_check #(95) w95(done[3]);
  vector_check #(129) w129(done[4]);

  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, w33.vector, w33.scalar, w33.vector_events, w33.mixed_events,
              w33.rise_events, w33.fall_events, w33.both_events,
              w33.vector_time, w33.mixed_time, w33.rise_time,
              w33.fall_time, w33.both_time);
    #20;
    if (done !== '1) $fatal(1, "Vector event checks did not finish");
    $display("Vector event checks: %0d", w7.checks + w33.checks + w65.checks
             + w95.checks + w129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module vector_check #(parameter WIDTH = 7) (output bit done = 0);
`ifdef EVENT_KNOWN_ONLY
  // The external two-state control uses only known values at every step.
  bit [WIDTH-1:0] vector = '0;
`else
  logic [WIDTH-1:0] vector = '0;
`endif
  bit scalar = 0;
  bit armed = 0;
  bit [31:0] checks = 0;
  bit [31:0] vector_events = 0, mixed_events = 0;
  bit [31:0] rise_events = 0, fall_events = 0, both_events = 0;
  time vector_time = 0, mixed_time = 0, rise_time = 0, fall_time = 0, both_time = 0;

  always @(vector) begin
    if (armed) begin
      vector_events++;
      vector_time = $time;
    end
  end
  always @(vector or scalar) begin
    if (armed) begin
      mixed_events++;
      mixed_time = $time;
    end
  end
  // Vector edge controls use the LSB, even when upper bits are X or Z.
  always @(posedge vector) begin
    if (armed) begin
      rise_events++;
      rise_time = $time;
    end
  end
  always @(negedge vector) begin
    if (armed) begin
      fall_events++;
      fall_time = $time;
    end
  end
  always @(posedge vector or negedge vector) begin
    if (armed) begin
      both_events++;
      both_time = $time;
    end
  end

  task automatic check_events(input bit [31:0] want_vector, want_mixed,
                              input time want_vector_time, want_mixed_time,
                              input bit [31:0] want_rise, want_fall, want_both,
                              input time want_rise_time, want_fall_time, want_both_time);
    `checkd(vector_events, want_vector);
    `checkd(mixed_events, want_mixed);
    `checkd(vector_time, want_vector_time);
    `checkd(mixed_time, want_mixed_time);
    `checkd(rise_events, want_rise);
    `checkd(fall_events, want_fall);
    `checkd(both_events, want_both);
    `checkd(rise_time, want_rise_time);
    `checkd(fall_time, want_fall_time);
    `checkd(both_time, want_both_time);
  endtask

  initial begin
    // Arm after startup, then drive on a later tick. Every checked event is
    // caused by an explicit input change while all observers are waiting.
    #1;
    armed = 1;
    #1;
    vector[WIDTH-1] = 1'b1;
    #1;
    check_events(1, 1, 2, 2, 0, 0, 0, 0, 0, 0);
    vector[WIDTH-1] = 1'b1;
    #1;
    check_events(1, 1, 2, 2, 0, 0, 0, 0, 0, 0);
    vector[WIDTH-1] = 1'b0;
    #1;
    check_events(2, 2, 4, 4, 0, 0, 0, 0, 0, 0);
`ifdef EVENT_KNOWN_ONLY
    vector[WIDTH-2] = 1'b1;
`else
    // 0->Z changes only the X/Z mask in the four-state encoding.
    vector[WIDTH-2] = 1'bz;
`endif
    #1;
    check_events(3, 3, 5, 5, 0, 0, 0, 0, 0, 0);
`ifdef EVENT_KNOWN_ONLY
    vector[WIDTH-2] = 1'b0;
`else
    vector[WIDTH-2] = 1'bx;
`endif
    #1;
    check_events(4, 4, 6, 6, 0, 0, 0, 0, 0, 0);
`ifdef EVENT_KNOWN_ONLY
    vector[WIDTH-2] = 1'b1;
`else
    // X->Z changes only the value half, with the X/Z mask still set.
    vector[WIDTH-2] = 1'bz;
`endif
    #1;
    check_events(5, 5, 7, 7, 0, 0, 0, 0, 0, 0);
`ifdef EVENT_KNOWN_ONLY
    vector[WIDTH-2] = 1'b1;
`else
    vector[WIDTH-2] = 1'bz;
`endif
    #1;
    check_events(5, 5, 7, 7, 0, 0, 0, 0, 0, 0);
    scalar = 1;
    #1;
    check_events(5, 6, 7, 9, 0, 0, 0, 0, 0, 0);
    vector[0] = 1'b1;
    #1;
    check_events(6, 7, 10, 10, 1, 0, 1, 10, 0, 10);
`ifdef EVENT_KNOWN_ONLY
    vector[WIDTH-1] = 1'b1;
`else
    vector[WIDTH-1] = 1'bx;
`endif
    #1;
    check_events(7, 8, 11, 11, 1, 0, 1, 10, 0, 10);
    vector[0] = 1'b0;
    #1;
    check_events(8, 9, 12, 12, 1, 1, 2, 10, 12, 12);
    scalar = 0;
    #1;
    check_events(8, 10, 12, 13, 1, 1, 2, 10, 12, 12);
    scalar = 0;
    vector[0] = 1'b0;
    #1;
    check_events(8, 10, 12, 13, 1, 1, 2, 10, 12, 12);
    vector[WIDTH-1] = 1'b0;
    #1;
    check_events(9, 11, 15, 15, 1, 1, 2, 10, 12, 12);
    vector[WIDTH-2] = 1'b0;
    #1;
    check_events(10, 12, 16, 16, 1, 1, 2, 10, 12, 12);
    `checkh(vector, {WIDTH{1'b0}});
    done = 1;
  end
endmodule
