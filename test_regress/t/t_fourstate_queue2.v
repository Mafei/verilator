// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

class token;
  bit [7:0] id;
  function new(bit [7:0] value);
    id = value;
  endfunction
endclass

module t;
  timeunit 1ns;
  timeprecision 1ns;
  bit [7:0] words[$];
  token tokens[$];
  process processes[$];
  bit [31:0] word_calls = 0;
  bit [31:0] index_calls = 0;
  bit [31:0] handle_calls = 0;
  bit [31:0] logic_calls = 0;
  bit acquired = 0;
  semaphore sem;
  token first;
  token second;
  token item;
  process here;
  process popped;
  bit [7:0] word;

  function automatic bit [7:0] next_word(bit [7:0] value);
    word_calls = word_calls + 1;
    return value;
  endfunction

  function automatic bit [31:0] next_index();
    index_calls = index_calls + 1;
    return 1;
  endfunction

  function automatic token next_handle(token value);
    handle_calls = handle_calls + 1;
    return value;
  endfunction

  function automatic logic [7:0] next_logic_word();
    logic_calls = logic_calls + 1;
    return 8'bz1x00101;
  endfunction

  initial begin
    words.push_back(next_word(8'h11));
    `checkh(word_calls, 32'd1);
    words.push_front(next_word(8'h22));
    `checkh(word_calls, 32'd2);
    `checkh(words.size(), 32'd2);
    word = words.pop_front();
    `checkh(word, 8'h22);
    word = words.pop_back();
    `checkh(word, 8'h11);
    `checkh(words.size(), 32'd0);
    words.push_back(next_word(8'h33));
    words.push_front(next_word(8'h44));
    words.push_back(next_word(8'h55));
    `checkh(word_calls, 32'd5);
    words.delete(next_index());
    `checkh(index_calls, 32'd1);
    `checkh(words.size(), 32'd2);
    word = words.pop_front();
    `checkh(word, 8'h44);
    word = words.pop_back();
    `checkh(word, 8'h55);
    words.push_back(next_word(8'h66));
    words.delete();
    `checkh(words.size(), 32'd0);
    `checkh(word_calls, 32'd6);

    // Queue elements are two-state; X/Z argument bits must convert to zero.
    words.push_back(8'hax);
    words.push_back(next_logic_word());
    `checkh(logic_calls, 32'd1);
    word = words.pop_front();
    `checkh(word, 8'ha0);
    word = words.pop_back();
    `checkh(word, 8'h45);
    `checkh(words.size(), 32'd0);

    first = new(8'h61);
    second = new(8'h72);
    tokens.push_back(next_handle(first));
    tokens.push_front(next_handle(second));
    `checkh(handle_calls, 32'd2);
    `checkh(tokens.size(), 32'd2);
    item = tokens.pop_front();
    if (item != second) `stop;
    `checkh(item.id, 8'h72);
    item = tokens.pop_back();
    if (item != first) `stop;
    `checkh(item.id, 8'h61);
    tokens.push_back(first);
    tokens.delete();
    `checkh(tokens.size(), 32'd0);

    here = process::self();
    if (!here) `stop;
    processes.push_front(here);
    processes.push_back(here);
    `checkh(processes.size(), 32'd2);
    popped = processes.pop_front();
    if (popped != here) `stop;
    popped = processes.pop_back();
    if (popped != here) `stop;
    `checkh(processes.size(), 32'd0);

    sem = new(0);
    fork
      begin
        sem.get(2);
        `checkh($time, 64'd4);
        acquired = 1;
      end
      begin
        #2;
        `checkh(acquired, 1'b0);
        sem.put(1);
        #2;
        `checkh(acquired, 1'b0);
        sem.put(1);
        #1;
        `checkh(acquired, 1'b1);
      end
    join
    `checkh(sem.try_get(), 32'd0);
    sem.put(3);
    `checkh(sem.try_get(2), 32'd1);
    `checkh(sem.try_get(1), 32'd1);
    `checkh(sem.try_get(1), 32'd0);
    $write("*-* All Finished *-*\n");
    $finish;
  end

  initial begin
    #20;
    `stop;
  end
endmodule
