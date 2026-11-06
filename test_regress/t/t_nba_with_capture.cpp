// DESCRIPTION: Verilator: Impure reduction index capture host
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

#include "verilated.h"

#include <cstdio>
#include VM_PREFIX_INCLUDE

int main(int argc, char** argv) {
    VerilatedContext context;
    context.threads(1);
    context.fatalOnError(false);
    context.commandArgs(argc, argv);
    VM_PREFIX model{&context};
    model.clk = 0;
    model.payload = 0;
    model.eval();
    if (context.gotError() || context.gotFinish() || model.calls != 0 || model.target0 != 0
        || model.target1 != 0)
        return 10;
    model.payload = 0x13579bdfU;
    model.clk = 1;
    model.eval();
    if (context.gotError() || context.gotFinish() || model.calls != 1
        || model.target0 != 0x13579bdfU || model.target1 != 0) {
        std::fprintf(stderr, "%%Error: first calls=%u target0=%x target1=%x\n",
                     static_cast<unsigned>(model.calls), static_cast<unsigned>(model.target0),
                     static_cast<unsigned>(model.target1));
        return 11;
    }
    model.clk = 0;
    model.eval();
    model.payload = 0x02468aceU;
    model.clk = 1;
    model.eval();
    if (context.gotError() || context.gotFinish() || model.calls != 2
        || model.target0 != 0x13579bdfU || model.target1 != 0x02468aceU) {
        std::fprintf(stderr, "%%Error: second calls=%u target0=%x target1=%x\n",
                     static_cast<unsigned>(model.calls), static_cast<unsigned>(model.target0),
                     static_cast<unsigned>(model.target1));
        return 12;
    }
    model.eval();
    if (context.gotError() || context.gotFinish() || context.time() != 0 || model.calls != 2
        || model.target0 != 0x13579bdfU || model.target1 != 0x02468aceU)
        return 13;
    model.final();
    std::puts("NBA impure reduction capture checks: 4");
    std::puts("*-* All Finished *-*");
    return 0;
}
