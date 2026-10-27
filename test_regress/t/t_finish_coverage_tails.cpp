// DESCRIPTION: Public timing-free clock and raw coverage writer
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
// The first application argument is the fresh raw coverage output path.
#include "verilated.h"
#include "verilated_cov.h"

#include "Vt_finish_coverage_tails.h"

#include <cstdio>

int main(int argc, char** argv) {
    if (argc < 2) return 2;
    VerilatedContext context;
    context.commandArgs(argc, argv);
    Vt_finish_coverage_tails model{&context};
    model.clk = 0;
    model.eval();
    for (unsigned edge = 0; edge < 8 && !context.gotFinish(); ++edge) {
        context.timeInc(5);
        model.clk = !model.clk;
        model.eval();
    }
    if (!context.gotFinish()) {
        std::puts("COV_EXTRA_ERROR missing finish within eight edges");
        return 2;
    }
    model.final();
    context.coveragep()->write(argv[1]);
    return context.gotError() ? 1 : 0;
}
