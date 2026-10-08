// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2021 Wilson Snyder
// SPDX-License-Identifier: CC0-1.0

// verilog_format: off
`define stop $stop
`define checkh(gotv, expv) do if ((gotv) !== (expv)) begin $write("%%Error: %s:%0d: got=%b expected=%b\n", `__FILE__, `__LINE__, (gotv), (expv)); `stop; end while (0);
// verilog_format: on

interface intf;
  logic [14:0] value;
endinterface

module fanout #(parameter int N = 1) (
  intf upstream,
  intf downstream[N-1:0]
);
  for (genvar i = 0; i < N; i++) assign downstream[i].value = upstream.value;
endmodule

module xbar(intf Masters[1:0]);
  intf demuxOut[7:0]();
  intf muxIn[7:0]();

  fanout #(.N(4)) fanout_inst0 (
    .upstream(Masters[0]),
    .downstream(demuxOut[3:0])
  );
  fanout #(.N(4)) fanout_inst1 (
    .upstream(Masters[1]),
    .downstream(demuxOut[7:4])
  );
  for (genvar slv = 0; slv < 4; slv++) begin
    for (genvar mst = 0; mst < 2; mst++) begin
      localparam int muxIdx = slv * 2 + mst;
      localparam int demuxIdx = slv + mst * 4;
      assign muxIn[muxIdx].value = demuxOut[demuxIdx].value;
    end
  end

  task automatic check_paths();
    `checkh(demuxOut[0].value, Masters[0].value);
    `checkh(demuxOut[1].value, Masters[0].value);
    `checkh(demuxOut[2].value, Masters[0].value);
    `checkh(demuxOut[3].value, Masters[0].value);
    `checkh(demuxOut[4].value, Masters[1].value);
    `checkh(demuxOut[5].value, Masters[1].value);
    `checkh(demuxOut[6].value, Masters[1].value);
    `checkh(demuxOut[7].value, Masters[1].value);
    `checkh(muxIn[0].value, Masters[0].value);
    `checkh(muxIn[1].value, Masters[1].value);
    `checkh(muxIn[2].value, Masters[0].value);
    `checkh(muxIn[3].value, Masters[1].value);
    `checkh(muxIn[4].value, Masters[0].value);
    `checkh(muxIn[5].value, Masters[1].value);
    `checkh(muxIn[6].value, Masters[0].value);
    `checkh(muxIn[7].value, Masters[1].value);
  endtask
endmodule

module t;
  intf masters[1:0]();
  logic [14:0] expected0;
  logic [14:0] expected1;
  xbar sub(.Masters(masters));

  initial begin
    for (int i = 0; i < 8; i++) begin
      case (i % 4)
        0: begin
          expected0 = 15'(i * 13 + 3);
          expected1 = 15'((i * 17) ^ 'h3456);
        end
        1: begin
          expected0 = 15'b101x001z1010010;
          expected1 = 15'b01zx11001100110;
        end
        2: begin
          expected0 = 'x;
          expected1 = 'z;
        end
        3: begin
          expected0 = 'z;
          expected1 = 'x;
        end
      endcase
      masters[0].value = expected0;
      masters[1].value = expected1;
      #1;
      `checkh(masters[0].value, expected0);
      `checkh(masters[1].value, expected1);
      sub.check_paths();
    end
    $write("*-* All Finished *-*\n");
    $finish;
  end
endmodule
