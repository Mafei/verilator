// DESCRIPTION: Verilator: No-timing NBA event capture host
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

#include "verilated.h"

#include <cstdio>
#include VM_PREFIX_INCLUDE

int main(int argc, char** argv) {
    for (unsigned mode = 0; mode < 2; ++mode) {
        VerilatedContext context;
        context.threads(1);
        context.fatalOnError(false);
        context.commandArgs(argc, argv);
        VM_PREFIX model{&context};
        model.route = 0;
        model.pattern = mode;
        for (unsigned evaluation = 0; evaluation < 2; ++evaluation) {
            model.eval();
            if (context.gotError() || context.gotFinish() || context.time() != 0
                || model.count0 != 1 || model.count1 != 0 || model.capture_ok != 1) {
                std::fprintf(stderr, "%%Error: mode=%u eval=%u count0=%u count1=%u capture=%u\n",
                             mode, evaluation, static_cast<unsigned>(model.count0),
                             static_cast<unsigned>(model.count1),
                             static_cast<unsigned>(model.capture_ok));
                return 10;
            }
        }
        model.final();
    }
    std::puts("NBA event capture checks: 4");
    std::puts("*-* All Finished *-*");
    return 0;
}
