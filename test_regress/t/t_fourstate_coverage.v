// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Antmicro
// SPDX-License-Identifier: CC0-1.0

module t;
    logic [1:0] ids[1];
    logic [1:0] matrix[2][4];
    axi_adapter dut(.priv_ids_i(ids), .priv_ids_i2(matrix));

    initial begin
        ids[0] = 2'bxz;
        foreach (matrix[row, column]) matrix[row][column] = 2'bzx;
        #1;
        if (dut.priv_ids_i[0] !== 2'bxz || dut.priv_ids_i2[1][3] !== 2'bzx) $stop;
        if (dut.exprstmt_lhs !== 4'd2 || dut.exprstmt_rhs !== 4'd2) $stop;
        ids[0] = 2'b10;
        matrix[1][3] = 2'b01;
        #1;
        if (dut.priv_ids_i[0] !== 2'b10 || dut.priv_ids_i2[1][3] !== 2'b01) $stop;
        $write("*-* All Finished *-*\n");
        $finish;
    end
endmodule

module axi_adapter(
    input logic [1:0] priv_ids_i[1],
    input logic [1:0] priv_ids_i2[2][4]
);
    logic unused_sig;
    logic [3:0] exprstmt_lhs;
    logic [3:0] exprstmt_rhs;

    assign unused_sig = 1;

    always_comb begin
        exprstmt_lhs = 1;
        exprstmt_rhs = (exprstmt_lhs += 1);
    end

    coverage_leaf xintr5(.clk(unused_sig));
endmodule

module coverage_leaf(
    input logic clk
);
    /*verilator no_inline_module*/
    logic unused_interrupt_sig;

    assign unused_interrupt_sig = clk;
endmodule
