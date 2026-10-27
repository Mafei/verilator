// DESCRIPTION: Public nested finish coverage and normal task return controls
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
// Runtime and source-span expectations are checked independently.
module t(input bit clk);
  int ticks = 0;
  int outer_hits = 0;
  int inner_hits = 0;
  int task_entries = 0;
  int task_returns = 0;
  int normal_tail = 0;

  task automatic maybe_finish(input bit request_finish,
                              input int tick_value, outer_value, inner_value,
                              input int entries_value, normal_tail_value,
                              input int returns_value);
    /*verilator no_inline_task*/
    if (request_finish) begin : task_finish_branch
      $display("COV_EXTRA_BEFORE_FINISH ticks=%0d outer=%0d inner=%0d task_entries=%0d task_returns=%0d normal_tail=%0d",
               tick_value, outer_value, inner_value, entries_value, returns_value, normal_tail_value);
      $finish(0);
    end
    // Meaningful normal-return source work, never executed by the finishing call.
    $display("COV_EXTRA_TASK_NORMAL_RETURN ticks=%0d task_entries=%0d task_returns=%0d normal_tail=%0d",  // COV_TASK_NORMAL_RETURN_TAIL
             tick_value, entries_value, returns_value, normal_tail_value);
  endtask

  always @(posedge clk) begin : clock_body
    ticks = ticks + 1;  // COV_CLOCK_BODY_PREFIX
    if (ticks == 1) begin : normal_branch
      task_entries = task_entries + 1;  // COV_CALLER_TASK_ENTRY_NORMAL
      maybe_finish(ticks == 4, ticks, outer_hits, inner_hits, task_entries,  // COV_NORMAL_CALL_FALSE
                   normal_tail, task_returns);
      task_returns = task_returns + 1;
      normal_tail = normal_tail + 1;  // COV_NORMAL_CALLER_FALLTHROUGH
      $display("COV_EXTRA_NORMAL ticks=%0d task_entries=%0d task_returns=%0d normal_tail=%0d",
               ticks, task_entries, task_returns, normal_tail);
    end
    if (ticks >= 2) begin : outer_branch
      outer_hits = outer_hits + 1;  // COV_OUTER_SELECTED_PREFIX
      if (ticks == 4) begin : inner_branch
        inner_hits = inner_hits + 1;  // COV_INNER_SELECTED_PREFIX
        task_entries = task_entries + 1;  // COV_CALLER_TASK_ENTRY_FINISH
        maybe_finish(ticks == 4, ticks, outer_hits, inner_hits, task_entries,  // COV_FINISHING_CALL_TRUE
                     normal_tail, task_returns);
      end
    end
  end

  final begin
    if (ticks != 4 || outer_hits != 3 || inner_hits != 1 || task_entries != 2
        || task_returns != 1 || normal_tail != 1) begin
      $fatal(1, "COV_EXTRA runtime control mismatch");
    end
    $display("COV_EXTRA_FINAL ticks=%0d outer=%0d inner=%0d task_entries=%0d task_returns=%0d normal_tail=%0d",
             ticks, outer_hits, inner_hits, task_entries, task_returns, normal_tail);
    $display("*-* All Finished *-*");
  end
endmodule
