// DESCRIPTION: Public delayed finish container with an unexecuted sibling barrier
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
// The delayed container and unexecuted sibling form a coverage barrier.
`timescale 1ns/1ns
module t(input bit arm);
  int entered = 0;
  initial begin : outer
    entered = entered + 1;  // COV_DELAY_OUTER_PREFIX
    if (arm) begin : selected
      $display("COV_DELAY_ENTER entered=%0d time=%0d", entered, $time);
      #1 $finish(0);  // COV_DELAY_FINISH_CONTAINER
      $display("COV_DELAY_DEAD_FUNCTIONAL_SIBLING");  // COV_DELAY_DEAD_SIBLING
      cover (1) $display("COV_DELAY_DEAD_COVER_ACTION");  // COV_DELAY_DEAD_USER_COVER
    end
  end
  final begin
    if (entered != 1) $fatal(1, "COV_DELAY unexpected runtime entry count");
    $display("COV_DELAY_FINAL entered=%0d time=%0d", entered, $time);
    $display("*-* All Finished *-*");
  end
endmodule
