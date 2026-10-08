// DESCRIPTION: Verilator: Dynamic packed index predicates retain their widths
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ps / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0)
// verilog_format: on

module packed_index_case #(
    parameter int WIDTH = 7,
    parameter int LOW = 3
) (
    output bit done
);
  int checks = 0;
  localparam int ADDR_WIDTH = $clog2(WIDTH);
  logic [WIDTH-1:0] descending = '0;
  logic [LOW:LOW+WIDTH-1] ascending = '0;
  logic [WIDTH-1:0] expected = '0;
  logic [ADDR_WIDTH-1:0] address = '0;
  logic [1:0] data = '0;
  logic clk = 0;
  logic we = 0;
  logic [ADDR_WIDTH-1:0] low_index, high_index;
  logic signed [31:0] bit_index = 0;
  logic [94:0] wide_index = 0;
  bit [0:0] narrow_index = 0;
  wire [1:0] pair_desc, pair_asc;
  wire bit_desc = descending[bit_index];
  wire bit_asc = ascending[LOW+WIDTH-1-bit_index];
  wire wide_bit = descending[wide_index];
  wire narrow_bit = descending[narrow_index];

  always @(address) begin
    low_index = ADDR_WIDTH'(2 * address);
    high_index = ADDR_WIDTH'(2 * address + 1);
  end
  always @(posedge clk) begin
    if (we) begin
      descending[low_index] <= #100 data[0];
      descending[high_index] <= #100 data[1];
      ascending[LOW+WIDTH-1-{{(32-ADDR_WIDTH) {1'b0}}, low_index}] <= #100 data[0];
      ascending[LOW+WIDTH-1-{{(32-ADDR_WIDTH) {1'b0}}, high_index}] <= #100 data[1];
    end
  end
  assign pair_desc[0] = descending[2*address];
  assign pair_desc[1] = descending[2*address+1];
  assign pair_asc[0] = ascending[LOW+WIDTH-1-2*address];
  assign pair_asc[1] = ascending[LOW+WIDTH-1-(2*address+1)];

  initial begin
    done = 0;
    address = 1;
    #100;
    address = 0;
    #100;
    for (int word_index = 0; word_index < WIDTH / 2; ++word_index) begin
      address = ADDR_WIDTH'(word_index);
      case (word_index % 4)
        0: data = 2'b10;
        1: data = 2'b01;
        2: data = 2'bxz;
        3: data = 2'bzx;
      endcase
      expected[2*word_index] = data[0];
      expected[2*word_index+1] = data[1];
      we = 1;
      #100;
      clk = 1;
      #50;
      // Change both operands while the delayed NBA is pending. Its address and data
      // must remain the values sampled at the clock edge.
      address = ADDR_WIDTH'((word_index + 1) % (WIDTH / 2));
      data = ~data;
      #100;
      clk = 0;
      #50;
      we = 0;
      `checkh(descending, expected);
      `checkh(ascending, expected);
      address = ADDR_WIDTH'(word_index);
      #50;
      `checkh(pair_desc, expected[2*word_index+:2]);
      `checkh(pair_asc, expected[2*word_index+:2]);
    end
    // Every pair is revisited independently after the varying-value writes.
    for (int word_index = 0; word_index < WIDTH / 2; ++word_index) begin
      address = ADDR_WIDTH'(word_index);
      #50;
      `checkh(pair_desc, expected[2*word_index+:2]);
      `checkh(pair_asc, expected[2*word_index+:2]);
    end
    address = 'x;
    #50;
    `checkh(pair_desc, 2'bxx);
    `checkh(pair_asc, 2'bxx);
    data = 2'b11;
    we = 1;
    clk = 1;
    #150;
    clk = 0;
    we = 0;
    `checkh(descending, expected);
    `checkh(ascending, expected);
    address = 'z;
    #50;
    `checkh(pair_desc, 2'bxx);
    `checkh(pair_asc, 2'bxx);
    data = 2'b00;
    we = 1;
    clk = 1;
    #150;
    clk = 0;
    we = 0;
    `checkh(descending, expected);
    `checkh(ascending, expected);
    bit_index = WIDTH - 1;
    #50;
    `checkh(bit_desc, 1'b0);
    `checkh(bit_asc, 1'b0);
    bit_index = -1;
    #50;
    `checkh(bit_desc, 1'bx);
    `checkh(bit_asc, 1'bx);
    bit_index = WIDTH;
    #50;
    `checkh(bit_desc, 1'bx);
    `checkh(bit_asc, 1'bx);
    wide_index = 95'd1 << 64;
    #50;
    `checkh(wide_bit, 1'bx);
    wide_index = 'x;
    #50;
    `checkh(wide_bit, 1'bx);
    wide_index = 'z;
    #50;
    `checkh(wide_bit, 1'bx);
    // A one-bit write index has a complete legal domain even for a much wider target.
    narrow_index = 0;
    #50;
    `checkh(narrow_bit, expected[0]);
    descending[narrow_index] = 1'bz;
    `checkh(descending[0], 1'bz);
    narrow_index = 1;
    #50;
    `checkh(narrow_bit, expected[1]);
    descending[narrow_index] = 1'bx;
    `checkh(descending[1], 1'bx);
    descending[narrow_index] = 1'b0;
    `checkh(descending[1], 1'b0);
    $display("CHECKS %m %0d", checks);
    done = 1;
  end
endmodule

// Keep the original minimal shape, including its six-bit derived write indexes.
module bare_packed_pair (
    output bit done
);
  int checks = 0;
  logic [63:0] storage = 0;
  logic [4:0] address = 0;
  logic [1:0] data = 0;
  logic clk = 0;
  logic we = 0;
  logic [5:0] lower_index, upper_index;
  wire [1:0] out;
  always @(address) begin
    lower_index = 2 * address;
    upper_index = 2 * address + 1;
  end
  always @(posedge clk) begin
    if (we) begin
      storage[lower_index] <= #100 data[0];
      storage[upper_index] <= #100 data[1];
    end
  end
  assign out[0] = storage[2*address];
  assign out[1] = storage[2*address+1];
  initial begin
    done = 0;
    #100;
    address = 1;
    #100;
    address = 0;
    #100;
    we = 1;
    data = 2'b10;
    #100;
    clk = 1;
    #150;
    clk = 0;
    `checkh(out, 2'b10);
    address = 31;
    data = 2'bxz;
    #100;
    clk = 1;
    #150;
    clk = 0;
    `checkh(out, 2'bxz);
    we = 0;
    address = 0;
    #100;
    `checkh(out, 2'b10);
    $display("CHECKS %m %0d", checks);
    done = 1;
  end
endmodule

module packed_index_once (
    output bit done
);
  int checks = 0;
  logic [6:0] source = 7'b10zx101;
  logic selected;
  bit [31:0] requested = 0;
  bit narrow_requested = 0;
  int calls = 0;

  function automatic bit [31:0] selected_index(input bit [31:0] index);
    calls++;
    return index;
  endfunction
  function automatic bit selected_narrow_index(input bit index);
    calls++;
    return index;
  endfunction

  initial begin
    done = 0;
    #100;
    for (int index = 0; index < 9; ++index) begin
      requested = 32'(index);
      calls = 0;
      selected = source[selected_index(requested)];
      `checkh(calls, 1);
      case (index)
        0, 2, 6: `checkh(selected, 1'b1);
        1, 5: `checkh(selected, 1'b0);
        3: `checkh(selected, 1'bx);
        4: `checkh(selected, 1'bz);
        default: `checkh(selected, 1'bx);
      endcase
      #100;
    end
    narrow_requested = 0;
    calls = 0;
    selected = source[selected_narrow_index(narrow_requested)];
    `checkh(calls, 1);
    `checkh(selected, 1'b1);
    narrow_requested = 1;
    calls = 0;
    selected = source[selected_narrow_index(narrow_requested)];
    `checkh(calls, 1);
    `checkh(selected, 1'b0);
    $display("CHECKS %m %0d", checks);
    done = 1;
  end
endmodule

module t;
  wire [6:0] done;
  packed_index_case #(
      .WIDTH(7),
      .LOW(3)
  ) c7 (
      done[0]
  );
  packed_index_case #(
      .WIDTH(33),
      .LOW(-2)
  ) c33 (
      done[1]
  );
  packed_index_case #(
      .WIDTH(65),
      .LOW(5)
  ) c65 (
      done[2]
  );
  packed_index_case #(
      .WIDTH(95),
      .LOW(9)
  ) c95 (
      done[3]
  );
  packed_index_case #(
      .WIDTH(31),
      .LOW(1)
  ) c31 (
      done[4]
  );
  bare_packed_pair bare (done[5]);
  packed_index_once once_case (done[6]);
  initial begin
    wait (&done);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
