// DESCRIPTION: Verilator: Constant clipped-select padding host
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

#include "verilated.h"

#include <cstdio>
#include VM_PREFIX_INCLUDE

int main(int argc, char** argv) {
    unsigned checks = 0;
    unsigned failures = 0;
    for (unsigned mode = 0; mode < 4; ++mode) {
        VerilatedContext context;
        context.threads(1);
        context.fatalOnError(false);
        context.commandArgs(argc, argv);
        VM_PREFIX model{&context};
        model.mode = mode;
        model.route = 0;
        model.seed = 0x13579bdf02468aceULL ^ mode;
        for (unsigned evaluation = 0; evaluation < 2; ++evaluation) {
            model.eval();
            ++checks;
            const bool passed = !context.gotError() && !context.gotFinish() && context.time() == 0
                                && model.exact_ok == 1 && model.other_ok == 1;
            if (!passed) ++failures;
            std::printf("PROBE mode=%u eval=%u exact=%u other=%u error=%u finish=%u pass=%u\n",
                        mode, evaluation, static_cast<unsigned>(model.exact_ok),
                        static_cast<unsigned>(model.other_ok),
                        static_cast<unsigned>(context.gotError()),
                        static_cast<unsigned>(context.gotFinish()), static_cast<unsigned>(passed));
        }
        model.final();
    }
    std::printf("Clipped constant padding checks: %u failures: %u modes: 4\n", checks, failures);
    if (checks != 8 || failures != 0) return 10;
    std::puts("*-* All Finished *-*");
    return 0;
}
