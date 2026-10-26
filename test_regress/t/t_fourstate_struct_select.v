// DESCRIPTION: Verilator: Variable writes through unpacked two-state struct fields
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: phase=%0d got=%b expected=%b\n", `__FILE__, `__LINE__, phase, (gotv), (expv)); `stop; end end while (0);
// verilog_format: on

module struct_select_case #(parameter int WIDTH = 7) (output bit done);
  typedef struct {
    bit [WIDTH-1:0] value;
    bit [WIDTH-1:0] words[0:2];
  } holder_t;
  class array_box_t;
    bit [WIDTH-1:0] words[0:2];
  endclass
  holder_t holder;
  array_box_t box;
  bit [WIDTH-1:0] expected = '0;
  bit [WIDTH-1:0] expected_words[0:2];
  int phase;
  int index;
  int captured_index;
  int array_index;
  int checks = 0;
  int rhs_calls = 0;

  function automatic bit [WIDTH-1:0] next_value;
    rhs_calls++;
    return WIDTH'(phase * 3 + 1);
  endfunction

  initial begin
    done = 0;
    box = new;
    holder.value = '0;
    for (int wordno = 0; wordno < 3; wordno++) begin
      holder.words[wordno] = '0;
      box.words[wordno] = '0;
      expected_words[wordno] = '0;
    end
    for (phase = 0; phase < 12; phase++) begin
      case (phase)
        5: index = WIDTH - 2;
        6: index = WIDTH - 1;
        7: index = WIDTH;
        8: index = WIDTH + 1;
        default: index = phase < 5 ? phase - 3 : phase - 6;
      endcase
      captured_index = index;
      #1;
      holder.value[index+:3] = 3'b101;
      for (int bitno = 0; bitno < 3; bitno++) begin
        if (index + bitno >= 0 && index + bitno < WIDTH)
          expected[index+bitno] = (bitno != 1);
      end
      `checkh(holder.value, expected);
      holder.value[index-:3] <= #1 3'b011;
      // Both the target index and value must be the delayed NBA's snapshots.
      index = WIDTH + 3;
      for (int bitno = 0; bitno < 3; bitno++) begin
        if (captured_index - 2 + bitno >= 0 && captured_index - 2 + bitno < WIDTH)
          expected[captured_index-2+bitno] = (bitno != 2);
      end
      #2;
      `checkh(holder.value, expected);
      array_index = phase % 5 - 1;
      holder.words[array_index] = next_value();
      box.words[array_index] = next_value();
      if (array_index >= 0 && array_index < 3)
        expected_words[array_index] = WIDTH'(phase * 3 + 1);
      for (int wordno = 0; wordno < 3; wordno++)
        `checkh(holder.words[wordno], expected_words[wordno]);
      for (int wordno = 0; wordno < 3; wordno++)
        `checkh(box.words[wordno], expected_words[wordno]);
      holder.words[array_index][phase%4+:3] = 3'b110;
      box.words[array_index][phase%4+:3] = 3'b110;
      if (array_index >= 0 && array_index < 3) begin
        for (int bitno = 0; bitno < 3; bitno++)
          expected_words[array_index][phase%4+bitno] = (bitno != 0);
      end
      for (int wordno = 0; wordno < 3; wordno++)
        `checkh(holder.words[wordno], expected_words[wordno]);
      for (int wordno = 0; wordno < 3; wordno++)
        `checkh(box.words[wordno], expected_words[wordno]);
      `checkh(rhs_calls, 2 * (phase + 1));
    end
    extra.run();
    $display("Struct selection W=%0d checks=%0d", WIDTH, checks);
    done = 1;
  end

  if (WIDTH >= 65) begin : extra
    localparam bit [32:0] P33 = {1'b1, 32'h96c35aa5};
    localparam bit [64:0] P65 = {1'b1, 64'ha5963cc3965aa5c3};
    task automatic run;
      for (int iteration = 0; iteration < 2; iteration++) begin
        index = iteration == 0 ? -7 : WIDTH - 9;
        #1;
        holder.value[index+:33] = P33;
        for (int bitno = 0; bitno < 33; bitno++) begin
          if (index + bitno >= 0 && index + bitno < WIDTH)
            expected[index+bitno] = P33[bitno];
        end
        `checkh(holder.value, expected);
        index = iteration == 0 ? -17 : WIDTH - 19;
        #1;
        holder.value[index+:65] = P65;
        for (int bitno = 0; bitno < 65; bitno++) begin
          if (index + bitno >= 0 && index + bitno < WIDTH)
            expected[index+bitno] = P65[bitno];
        end
        `checkh(holder.value, expected);
      end
    endtask
  end else begin : extra
    task automatic run;
    endtask
  end
endmodule

module t;
  wire [5:0] done;
  struct_select_case #(7) s7(done[0]);
  struct_select_case #(15) s15(done[1]);
  struct_select_case #(31) s31(done[2]);
  struct_select_case #(33) s33(done[3]);
  struct_select_case #(65) s65(done[4]);
  struct_select_case #(95) s95(done[5]);
  initial begin
    #100;
    if (done !== 6'b111111) `stop;
    $display("Struct selection profiles: 6");
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
