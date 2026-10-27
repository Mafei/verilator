// DESCRIPTION: Public timing-aware driver for the coverage container barrier
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
// Advance to the actual next scheduled event without fixed settling.
#include "verilated.h"
#include "verilated_cov.h"

#include "Vt_finish_coverage_barrier.h"

#include <cstdio>

int main(int argc, char** argv) {
    if (argc < 2) return 2;
    VerilatedContext context;
    context.commandArgs(argc, argv);
    Vt_finish_coverage_barrier model{&context};
    model.arm = 1;
    while (!context.gotFinish()) {
        model.eval();
        if (context.gotFinish()) break;
        if (!model.eventsPending()) {
            std::puts("COV_DELAY_ERROR no pending event before finish");
            return 2;
        }
        const uint64_t next = model.nextTimeSlot();
        if (next <= context.time() || next > 16) {
            std::puts("COV_DELAY_ERROR invalid or excessive next time slot");
            return 2;
        }
        context.time(next);
    }
    model.final();
    context.coveragep()->write(argv[1]);
    return context.gotError() ? 1 : 0;
}
