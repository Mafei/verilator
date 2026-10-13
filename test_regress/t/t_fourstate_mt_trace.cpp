// DESCRIPTION: Verilator: Deterministic MT trace clock driver
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

#include <verilated.h>
#include <verilated_vcd_c.h>

#include VM_PREFIX_INCLUDE

#include <memory>

int main(int argc, char** argv) {
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
    contextp->threads(2);
    contextp->commandArgs(argc, argv);
    contextp->traceEverOn(true);
    const std::unique_ptr<VM_PREFIX> topp{new VM_PREFIX{contextp.get(), "t"}};
    if (topp->threads() != 2) return 2;
    const std::unique_ptr<VerilatedVcdC> tracep{new VerilatedVcdC};
    topp->trace(tracep.get(), 99);
    tracep->open(VL_STRINGIFY(TEST_OBJ_DIR) "/simx.vcd");
    for (unsigned int time = 0; time <= 11; ++time) {
        contextp->time(time);
        topp->clk = time % 2;
        topp->eval();
        tracep->dump(time);
    }
    topp->final();
    tracep->close();
    VL_PRINTF("*-* All Finished *-*\n");
    return 0;
}
