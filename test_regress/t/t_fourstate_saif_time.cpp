// -*- mode: C++; c-file-style: "cc-mode" -*-
//
// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Wilson Snyder
// SPDX-License-Identifier: CC0-1.0

#include <verilated.h>
#include <verilated_saif_c.h>

#include <array>
#include <cstdio>
#include <string>

// Exercise the runtime trace interface directly, independently of SV lowering.
static constexpr std::array<unsigned, 7> widths{{1, 7, 15, 31, 33, 65, 95}};
static constexpr uint32_t codesPerSignal = 8;

struct Stimulus final {
    uint32_t baseCode = 0;
    unsigned phase = 0;
};

static void traceInit(void* userp, VerilatedSaif* tracep, uint32_t baseCode) {
    Stimulus& stimulus = *static_cast<Stimulus*>(userp);
    stimulus.baseCode = baseCode;
    tracep->pushPrefix("t", VerilatedTracePrefixType::SCOPE_MODULE);
    for (unsigned kind = 0; kind < 2; ++kind) {
        for (unsigned i = 0; i < widths.size(); ++i) {
            const unsigned width = widths[i];
            const uint32_t code = baseCode + (kind * widths.size() + i) * codesPerSignal;
            const std::string name = std::string{kind ? "k" : "s"} + std::to_string(width);
            if (width == 1) {
                tracep->declBit(code, 0, name.c_str());
            } else if (width <= 32) {
                tracep->declBus(code, 0, name.c_str(), width - 1, 0);
            } else if (width <= 64) {
                tracep->declQuad(code, 0, name.c_str(), width - 1, 0);
            } else {
                tracep->declWide(code, 0, name.c_str(), width - 1, 0);
            }
        }
    }
    tracep->popPrefix();
}

template <bool Full>
static void traceValues(void* userp, VerilatedSaif::Buffer* bufp) {
    const Stimulus& stimulus = *static_cast<Stimulus*>(userp);
    for (unsigned kind = 0; kind < 2; ++kind) {
        for (unsigned i = 0; i < widths.size(); ++i) {
            const unsigned width = widths[i];
            uint32_t* const oldp
                = bufp->oldp(stimulus.baseCode + (kind * widths.size() + i) * codesPerSignal);
            VlWide<3> value{};
            VlWide<3> xz{};
            for (unsigned bit = 0; bit < width; ++bit) {
                // Four-state order: 0, 1, X, Z; two-state order: 0, 1.
                const unsigned state = (bit + stimulus.phase) % (kind ? 2 : 4);
                const EData mask = EData{1} << (bit % VL_EDATASIZE);
                if (state == 1 || state == 2) value[bit / VL_EDATASIZE] |= mask;
                if (state >= 2) xz[bit / VL_EDATASIZE] |= mask;
            }
            const QData qvalue = (QData{value[1]} << VL_EDATASIZE) | value[0];
            const QData qxz = (QData{xz[1]} << VL_EDATASIZE) | xz[0];
            if (!kind) {
                if (width == 1) {
                    if (Full)
                        bufp->fullLogic(oldp, value[0], xz[0]);
                    else
                        bufp->chgLogic(oldp, value[0], xz[0]);
                } else if (width <= 8) {
                    if (Full)
                        bufp->fullFourstateCData(oldp, value[0], xz[0], width);
                    else
                        bufp->chgFourstateCData(oldp, value[0], xz[0], width);
                } else if (width <= 16) {
                    if (Full)
                        bufp->fullFourstateSData(oldp, value[0], xz[0], width);
                    else
                        bufp->chgFourstateSData(oldp, value[0], xz[0], width);
                } else if (width <= 32) {
                    if (Full)
                        bufp->fullFourstateIData(oldp, value[0], xz[0], width);
                    else
                        bufp->chgFourstateIData(oldp, value[0], xz[0], width);
                } else if (width <= 64) {
                    if (Full)
                        bufp->fullFourstateQData(oldp, qvalue, qxz, width);
                    else
                        bufp->chgFourstateQData(oldp, qvalue, qxz, width);
                } else {
                    if (Full)
                        bufp->fullFourstateWData(oldp, value, xz, width);
                    else
                        bufp->chgFourstateWData(oldp, value, xz, width);
                }
            } else {
                if (width == 1) {
                    if (Full)
                        bufp->fullBit(oldp, value[0]);
                    else
                        bufp->chgBit(oldp, value[0]);
                } else if (width <= 8) {
                    if (Full)
                        bufp->fullCData(oldp, value[0], width);
                    else
                        bufp->chgCData(oldp, value[0], width);
                } else if (width <= 16) {
                    if (Full)
                        bufp->fullSData(oldp, value[0], width);
                    else
                        bufp->chgSData(oldp, value[0], width);
                } else if (width <= 32) {
                    if (Full)
                        bufp->fullIData(oldp, value[0], width);
                    else
                        bufp->chgIData(oldp, value[0], width);
                } else if (width <= 64) {
                    if (Full)
                        bufp->fullQData(oldp, qvalue, width);
                    else
                        bufp->chgQData(oldp, qvalue, width);
                } else {
                    if (Full)
                        bufp->fullWData(oldp, value, width);
                    else
                        bufp->chgWData(oldp, value, width);
                }
            }
        }
    }
}

static void runTrace(const char* filename, uint64_t closeTime) {
    Stimulus stimulus;
    VerilatedSaifC trace;
    trace.set_time_unit("1ns");
    trace.set_time_resolution("1ns");
    trace.spTrace()->addInitCb(traceInit, &stimulus, "t", false,
                               2 * widths.size() * codesPerSignal);
    trace.spTrace()->addFullCb(traceValues<true>, 0, &stimulus);
    trace.spTrace()->addChgCb(traceValues<false>, 0, &stimulus);
    trace.open(filename);
    if (!trace.isOpen()) VL_FATAL_MT(__FILE__, __LINE__, "", "SAIF open failed");
    const std::array<uint64_t, 5> times{{0, 3, 8, 15, 26}};
    for (unsigned phase = 0; phase < times.size(); ++phase) {
        stimulus.phase = phase;
        trace.dump(times[phase]);
    }
    // Advance time without changing any bit, including bits whose last state is X/Z.
    if (closeTime > times.back()) trace.dump(closeTime);
    trace.close();
    trace.close();  // Repeated close must not alter already finalized statistics.
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    runTrace(VL_STRINGIFY(TEST_OBJ_DIR) "/simx_short.saif", 26);
    runTrace(VL_STRINGIFY(TEST_OBJ_DIR) "/simx.saif", 39);
    std::printf("*-* All Finished *-*\n");
    return 0;
}
