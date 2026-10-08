// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns / 1ps
// verilog_format: off
`define stop $stop
`define checkh(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define checkd(gotv,expv) do begin checks++; if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%0d expected=%0d\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end end while (0);
`define STRINGIFY(x) `"x`"
// verilog_format: on

module t;
  wire [5:0] done;
  cond_width #(1) w1 (done[0]);
  cond_width #(7) w7 (done[1]);
  cond_width #(33) w33 (done[2]);
  cond_width #(65) w65 (done[3]);
  cond_width #(95) w95 (done[4]);
  cond_width #(129) w129 (done[5]);
  initial begin
    $dumpfile(`STRINGIFY(`TEST_DUMPFILE));
    $dumpvars(0, t);
    #100;
    if (done !== '1) $fatal(1, "Conditional scale regression did not finish");
    $display("Conditional scale checks: %0d",
             w1.checks + w7.checks + w33.checks + w65.checks + w95.checks + w129.checks);
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule

module cond_width #(
    parameter int WIDTH = 1
) (
    output bit done = 0
);
  typedef logic [WIDTH-1:0] word_t;
  typedef logic [0:WIDTH-1] up_word_t;
  bit [31:0] checks = 0;
  logic [127:0] guards = '0;
  logic selector, inner_selector;
  word_t left_value, middle_value, right_value;
  word_t result20 = '0, result32 = '0, result64 = '0, result128 = '0;
  word_t function_result = '0, nested_result = '0;
  word_t vector7_result = '0, vector65_result = '0;
  logic [6:0] vector7_selector;
  logic [64:0] vector65_selector;
  up_word_t up_left, up_right, up_result = '0, up_wanted;
  bit [31:0] condition_calls = 0, inner_calls = 0;
  bit [31:0] left_calls = 0, middle_calls = 0, right_calls = 0;

  function automatic logic state_code(input int code);
    case (code)
      0: return 1'b0;
      1: return 1'b1;
      2: return 1'bx;
      3: return 1'bz;
      default: return 1'bx;
    endcase
  endfunction

  // Literal merge oracle; unknown predicates never merge two common Z bits.
  // This literal table has no knowledge of the compiler value/mask encoding.
  function automatic logic merged_bit(input logic a, b);
    case ({
      a, b
    })
      2'b00: return 1'b0;
      2'b11: return 1'b1;
      2'bxx: return 1'bx;
      2'bzz: return 1'bz;
      default: return 1'bx;
    endcase
  endfunction

  function automatic word_t merged_word(input word_t a, b);
    word_t result;
    for (int bitno = 0; bitno < WIDTH; bitno++) result[bitno] = merged_bit(a[bitno], b[bitno]);
    return result;
  endfunction

  function automatic word_t pattern(input int phase, flavor);
    word_t result;
    for (int bitno = 0; bitno < WIDTH; bitno++) begin
      if ((flavor == 1) && ((phase % 4) == 2) && ((bitno % 2) == 0))
        result[bitno] = state_code((bitno + phase) % 4);
      else result[bitno] = state_code((bitno + phase + flavor) % 4);
      // These phases merge a selected word with itself below an unknown guard.
      // Keep their data at 0/1/X while the equal-Z conditional rule is unsettled.
      if (((phase % 8) == 5 || (phase % 8) == 6) && result[bitno] === 1'bz) result[bitno] = 1'bx;
    end
    return result;
  endfunction

  function automatic logic condition(input logic value);
    condition_calls++;
    return value;
  endfunction

  function automatic logic inner_condition(input logic value);
    inner_calls++;
    return value;
  endfunction

  function automatic logic [6:0] vector7_condition(input logic [6:0] value);
    condition_calls++;
    return value;
  endfunction

  function automatic logic [64:0] vector65_condition(input logic [64:0] value);
    condition_calls++;
    return value;
  endfunction

  function automatic word_t left_branch();
    left_calls++;
    return left_value;
  endfunction

  function automatic word_t middle_branch();
    middle_calls++;
    return middle_value;
  endfunction

  function automatic word_t right_branch();
    right_calls++;
    return right_value;
  endfunction

  function automatic word_t chain20(input logic [127:0] select_bits, input word_t selected,
                                    fallback);
    return
      select_bits[0] ? selected :
      select_bits[1] ? selected :
      select_bits[2] ? selected :
      select_bits[3] ? selected :
      select_bits[4] ? selected :
      select_bits[5] ? selected :
      select_bits[6] ? selected :
      select_bits[7] ? selected :
      select_bits[8] ? selected :
      select_bits[9] ? selected :
      select_bits[10] ? selected :
      select_bits[11] ? selected :
      select_bits[12] ? selected :
      select_bits[13] ? selected :
      select_bits[14] ? selected :
      select_bits[15] ? selected :
      select_bits[16] ? selected :
      select_bits[17] ? selected :
      select_bits[18] ? selected :
      select_bits[19] ? selected :
      fallback;
  endfunction

  function automatic word_t chain32(input logic [127:0] select_bits, input word_t selected,
                                    fallback);
    return
      select_bits[0] ? selected :
      select_bits[1] ? selected :
      select_bits[2] ? selected :
      select_bits[3] ? selected :
      select_bits[4] ? selected :
      select_bits[5] ? selected :
      select_bits[6] ? selected :
      select_bits[7] ? selected :
      select_bits[8] ? selected :
      select_bits[9] ? selected :
      select_bits[10] ? selected :
      select_bits[11] ? selected :
      select_bits[12] ? selected :
      select_bits[13] ? selected :
      select_bits[14] ? selected :
      select_bits[15] ? selected :
      select_bits[16] ? selected :
      select_bits[17] ? selected :
      select_bits[18] ? selected :
      select_bits[19] ? selected :
      select_bits[20] ? selected :
      select_bits[21] ? selected :
      select_bits[22] ? selected :
      select_bits[23] ? selected :
      select_bits[24] ? selected :
      select_bits[25] ? selected :
      select_bits[26] ? selected :
      select_bits[27] ? selected :
      select_bits[28] ? selected :
      select_bits[29] ? selected :
      select_bits[30] ? selected :
      select_bits[31] ? selected :
      fallback;
  endfunction

  function automatic word_t chain64(input logic [127:0] select_bits, input word_t selected,
                                    fallback);
    return
      select_bits[0] ? selected :
      select_bits[1] ? selected :
      select_bits[2] ? selected :
      select_bits[3] ? selected :
      select_bits[4] ? selected :
      select_bits[5] ? selected :
      select_bits[6] ? selected :
      select_bits[7] ? selected :
      select_bits[8] ? selected :
      select_bits[9] ? selected :
      select_bits[10] ? selected :
      select_bits[11] ? selected :
      select_bits[12] ? selected :
      select_bits[13] ? selected :
      select_bits[14] ? selected :
      select_bits[15] ? selected :
      select_bits[16] ? selected :
      select_bits[17] ? selected :
      select_bits[18] ? selected :
      select_bits[19] ? selected :
      select_bits[20] ? selected :
      select_bits[21] ? selected :
      select_bits[22] ? selected :
      select_bits[23] ? selected :
      select_bits[24] ? selected :
      select_bits[25] ? selected :
      select_bits[26] ? selected :
      select_bits[27] ? selected :
      select_bits[28] ? selected :
      select_bits[29] ? selected :
      select_bits[30] ? selected :
      select_bits[31] ? selected :
      select_bits[32] ? selected :
      select_bits[33] ? selected :
      select_bits[34] ? selected :
      select_bits[35] ? selected :
      select_bits[36] ? selected :
      select_bits[37] ? selected :
      select_bits[38] ? selected :
      select_bits[39] ? selected :
      select_bits[40] ? selected :
      select_bits[41] ? selected :
      select_bits[42] ? selected :
      select_bits[43] ? selected :
      select_bits[44] ? selected :
      select_bits[45] ? selected :
      select_bits[46] ? selected :
      select_bits[47] ? selected :
      select_bits[48] ? selected :
      select_bits[49] ? selected :
      select_bits[50] ? selected :
      select_bits[51] ? selected :
      select_bits[52] ? selected :
      select_bits[53] ? selected :
      select_bits[54] ? selected :
      select_bits[55] ? selected :
      select_bits[56] ? selected :
      select_bits[57] ? selected :
      select_bits[58] ? selected :
      select_bits[59] ? selected :
      select_bits[60] ? selected :
      select_bits[61] ? selected :
      select_bits[62] ? selected :
      select_bits[63] ? selected :
      fallback;
  endfunction

  function automatic word_t chain128(input logic [127:0] select_bits, input word_t selected,
                                     fallback);
    return
      select_bits[0] ? selected :
      select_bits[1] ? selected :
      select_bits[2] ? selected :
      select_bits[3] ? selected :
      select_bits[4] ? selected :
      select_bits[5] ? selected :
      select_bits[6] ? selected :
      select_bits[7] ? selected :
      select_bits[8] ? selected :
      select_bits[9] ? selected :
      select_bits[10] ? selected :
      select_bits[11] ? selected :
      select_bits[12] ? selected :
      select_bits[13] ? selected :
      select_bits[14] ? selected :
      select_bits[15] ? selected :
      select_bits[16] ? selected :
      select_bits[17] ? selected :
      select_bits[18] ? selected :
      select_bits[19] ? selected :
      select_bits[20] ? selected :
      select_bits[21] ? selected :
      select_bits[22] ? selected :
      select_bits[23] ? selected :
      select_bits[24] ? selected :
      select_bits[25] ? selected :
      select_bits[26] ? selected :
      select_bits[27] ? selected :
      select_bits[28] ? selected :
      select_bits[29] ? selected :
      select_bits[30] ? selected :
      select_bits[31] ? selected :
      select_bits[32] ? selected :
      select_bits[33] ? selected :
      select_bits[34] ? selected :
      select_bits[35] ? selected :
      select_bits[36] ? selected :
      select_bits[37] ? selected :
      select_bits[38] ? selected :
      select_bits[39] ? selected :
      select_bits[40] ? selected :
      select_bits[41] ? selected :
      select_bits[42] ? selected :
      select_bits[43] ? selected :
      select_bits[44] ? selected :
      select_bits[45] ? selected :
      select_bits[46] ? selected :
      select_bits[47] ? selected :
      select_bits[48] ? selected :
      select_bits[49] ? selected :
      select_bits[50] ? selected :
      select_bits[51] ? selected :
      select_bits[52] ? selected :
      select_bits[53] ? selected :
      select_bits[54] ? selected :
      select_bits[55] ? selected :
      select_bits[56] ? selected :
      select_bits[57] ? selected :
      select_bits[58] ? selected :
      select_bits[59] ? selected :
      select_bits[60] ? selected :
      select_bits[61] ? selected :
      select_bits[62] ? selected :
      select_bits[63] ? selected :
      select_bits[64] ? selected :
      select_bits[65] ? selected :
      select_bits[66] ? selected :
      select_bits[67] ? selected :
      select_bits[68] ? selected :
      select_bits[69] ? selected :
      select_bits[70] ? selected :
      select_bits[71] ? selected :
      select_bits[72] ? selected :
      select_bits[73] ? selected :
      select_bits[74] ? selected :
      select_bits[75] ? selected :
      select_bits[76] ? selected :
      select_bits[77] ? selected :
      select_bits[78] ? selected :
      select_bits[79] ? selected :
      select_bits[80] ? selected :
      select_bits[81] ? selected :
      select_bits[82] ? selected :
      select_bits[83] ? selected :
      select_bits[84] ? selected :
      select_bits[85] ? selected :
      select_bits[86] ? selected :
      select_bits[87] ? selected :
      select_bits[88] ? selected :
      select_bits[89] ? selected :
      select_bits[90] ? selected :
      select_bits[91] ? selected :
      select_bits[92] ? selected :
      select_bits[93] ? selected :
      select_bits[94] ? selected :
      select_bits[95] ? selected :
      select_bits[96] ? selected :
      select_bits[97] ? selected :
      select_bits[98] ? selected :
      select_bits[99] ? selected :
      select_bits[100] ? selected :
      select_bits[101] ? selected :
      select_bits[102] ? selected :
      select_bits[103] ? selected :
      select_bits[104] ? selected :
      select_bits[105] ? selected :
      select_bits[106] ? selected :
      select_bits[107] ? selected :
      select_bits[108] ? selected :
      select_bits[109] ? selected :
      select_bits[110] ? selected :
      select_bits[111] ? selected :
      select_bits[112] ? selected :
      select_bits[113] ? selected :
      select_bits[114] ? selected :
      select_bits[115] ? selected :
      select_bits[116] ? selected :
      select_bits[117] ? selected :
      select_bits[118] ? selected :
      select_bits[119] ? selected :
      select_bits[120] ? selected :
      select_bits[121] ? selected :
      select_bits[122] ? selected :
      select_bits[123] ? selected :
      select_bits[124] ? selected :
      select_bits[125] ? selected :
      select_bits[126] ? selected :
      select_bits[127] ? selected :
      fallback;
  endfunction

  initial begin
    word_t wanted, got, inner_wanted;
    bit [31:0] want_inner, want_left, want_middle, want_right;
    int length;
    for (int phase = 0; phase < 32; phase++) begin
      #1;
      left_value = pattern(phase, 0);
      right_value = pattern(phase, 1);
      middle_value = pattern(phase, 2);
      for (int depth = 0; depth < 4; depth++) begin
        case (depth)
          0: length = 20;
          1: length = 32;
          2: length = 64;
          3: length = 128;
        endcase
        guards = '0;
        case (phase % 8)
          0: wanted = right_value;
          1: begin
            guards[0] = 1'b1;
            wanted = left_value;
          end
          2: begin
            guards[length-1] = 1'b1;
            wanted = left_value;
          end
          3: begin
            guards[(phase*3)%length] = 1'bx;
            wanted = merged_word(left_value, right_value);
          end
          4: begin
            guards[(phase*3)%length] = 1'bz;
            wanted = merged_word(left_value, right_value);
          end
          5: begin
            guards[0] = 1'bx;
            guards[length-1] = 1'b1;
            wanted = left_value;
          end
          6: begin
            guards[0] = 1'bz;
            guards[length-1] = 1'b1;
            wanted = left_value;
          end
          7: begin
            guards = 'x;
            wanted = merged_word(left_value, right_value);
          end
        endcase
        case (depth)
          0: begin
            result20 = chain20(guards, left_value, right_value);
            got = result20;
          end
          1: begin
            result32 = chain32(guards, left_value, right_value);
            got = result32;
          end
          2: begin
            result64 = chain64(guards, left_value, right_value);
            got = result64;
          end
          3: begin
            result128 = chain128(guards, left_value, right_value);
            got = result128;
          end
        endcase
        `checkh(got, wanted);
      end

      selector = state_code(phase % 4);
      inner_selector = state_code((phase / 4) % 4);
      up_left = left_value;
      up_right = right_value;
      case (selector)
        1'b0: wanted = right_value;
        1'b1: wanted = left_value;
        default: wanted = merged_word(left_value, right_value);
      endcase
      up_wanted = wanted;
      up_result = selector ? up_left : up_right;
      `checkh(up_result, up_wanted);

      condition_calls = 0;
      left_calls = 0;
      right_calls = 0;
      function_result = condition(selector) ? left_branch() : right_branch();
      `checkh(function_result, wanted);
      `checkd(condition_calls, 1);
      `checkd(left_calls, selector !== 1'b0 ? 1 : 0);
      `checkd(right_calls, selector !== 1'b1 ? 1 : 0);

      // A known one makes a vector true even when other bits contain X/Z.
      // Unknown predicates have no known one; their required branches run once.
      case (phase % 8)
        0: begin
          vector7_selector = '0;
          vector65_selector = '0;
        end
        1: begin
          vector7_selector = '0;
          vector65_selector = '0;
          vector7_selector[0] = 1'b1;
          vector65_selector[0] = 1'b1;
        end
        2: begin
          vector7_selector = 'x;
          vector65_selector = 'x;
        end
        3: begin
          vector7_selector = 'z;
          vector65_selector = 'z;
        end
        4: begin
          vector7_selector = 'x;
          vector65_selector = 'x;
          vector7_selector[3] = 1'b1;
          vector65_selector[32] = 1'b1;
        end
        5: begin
          vector7_selector = 'z;
          vector65_selector = 'z;
          vector7_selector[6] = 1'b1;
          vector65_selector[64] = 1'b1;
        end
        6: begin
          vector7_selector = '0;
          vector65_selector = '0;
          vector7_selector[0] = 1'bx;
          vector65_selector[0] = 1'bx;
        end
        7: begin
          vector7_selector = '0;
          vector65_selector = '0;
          vector7_selector[6] = 1'bz;
          vector65_selector[64] = 1'bz;
        end
      endcase
      case (phase % 8)
        0: begin
          wanted = right_value;
          want_left = 0;
          want_right = 1;
        end
        1, 4, 5: begin
          wanted = left_value;
          want_left = 1;
          want_right = 0;
        end
        default: begin
          wanted = merged_word(left_value, right_value);
          want_left = 1;
          want_right = 1;
        end
      endcase
      condition_calls = 0;
      left_calls = 0;
      right_calls = 0;
      vector7_result = vector7_condition(vector7_selector) ? left_branch() : right_branch();
      `checkh(vector7_result, wanted);
      `checkd(condition_calls, 1);
      `checkd(left_calls, want_left);
      `checkd(right_calls, want_right);
      condition_calls = 0;
      left_calls = 0;
      right_calls = 0;
      vector65_result = vector65_condition(vector65_selector) ? left_branch() : right_branch();
      `checkh(vector65_result, wanted);
      `checkd(condition_calls, 1);
      `checkd(left_calls, want_left);
      `checkd(right_calls, want_right);

      // Nested unknown conditions must evaluate each required branch only once.
      condition_calls = 0;
      inner_calls = 0;
      left_calls = 0;
      middle_calls = 0;
      right_calls = 0;
      case (inner_selector)
        1'b0: inner_wanted = right_value;
        1'b1: inner_wanted = middle_value;
        default: inner_wanted = merged_word(middle_value, right_value);
      endcase
      case (selector)
        1'b0: wanted = inner_wanted;
        1'b1: wanted = left_value;
        default: wanted = merged_word(left_value, inner_wanted);
      endcase
      want_inner = selector !== 1'b1 ? 1 : 0;
      want_left = selector !== 1'b0 ? 1 : 0;
      want_middle = ((want_inner != 0) && (inner_selector !== 1'b0)) ? 1 : 0;
      want_right = ((want_inner != 0) && (inner_selector !== 1'b1)) ? 1 : 0;
      nested_result = condition(selector) ?
          left_branch() : (inner_condition(inner_selector) ? middle_branch() : right_branch());
      `checkh(nested_result, wanted);
      `checkd(condition_calls, 1);
      `checkd(inner_calls, want_inner);
      `checkd(left_calls, want_left);
      `checkd(middle_calls, want_middle);
      `checkd(right_calls, want_right);
    end
    done = 1;
  end
endmodule
