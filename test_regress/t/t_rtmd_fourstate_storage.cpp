// -*- mode: C++; c-file-style: "cc-mode" -*-
//
// DESCRIPTION: Verilator: Verilog Test module
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Wilson Snyder
// SPDX-License-Identifier: CC0-1.0

#include <verilated.h>
#include <verilated_fst_c.h>
#include <verilated_rtmd.h>
#include <verilated_saif_c.h>
#include <verilated_vcd_c.h>

#include <array>
#include <cstdio>
#include <memory>
#include <string>
#include <vector>

// Independent runtime fixture: all three four-state names deliberately share
// the *same* value address; only a real alias also shares the X/Z address.
static constexpr std::array<unsigned, 16> widths{
    {1, 7, 8, 9, 15, 31, 32, 33, 64, 65, 95, 128, 129, 256, 257, 301}};
struct Storage final {
    EData value[16][10]{};
    EData known[16][10]{};
    EData xz[16][10]{};
    EData otherXZ[16][10]{};
};

class StorageModel final : public VerilatedModel {
    Storage m_storage;
    std::vector<std::string> m_names;
    std::vector<VlRtmdDataTypeRow> m_types;
    std::vector<VlRtmdVarTypeRow> m_varTypes;
    std::vector<VlRtmdHierRow> m_hierarchy;
    const VlRtmdDataTypeRow* m_typeChunk = nullptr;
    const VlRtmdVarTypeRow* m_varTypeChunk = nullptr;
    const VlRtmdHierRow* m_hierChunk = nullptr;
    void evalBegin() override {}
    void evalEnd() override {}
    void evalStatic() override {}
    void evalInitial() override {}
    void evalSample() override {}
    bool evalStl(bool) override { return false; }
    bool evalIco(bool) override { return false; }
    bool evalAct() override { return false; }
    bool evalInact() override { return false; }
    bool evalNba() override { return false; }
    bool evalObs() override { return false; }
    bool evalReact() override { return false; }
    void evalPostponed() override {}
    void dumpTriggersStl() override {}
    void dumpTriggersIco() override {}
    void dumpTriggersAct() override {}
    void dumpTriggersNba() override {}
    void dumpTriggersObs() override {}
    void dumpTriggersReact() override {}
    void evalFinal() override {}

public:
    const char* hierName() const override { return "t"; }
    const char* modelName() const override { return "StorageModel"; }
    unsigned threads() const override { return 1; }
    explicit StorageModel(VerilatedContext& context)
        : VerilatedModel{context} {
        m_names.reserve(4 * widths.size());
        m_types.emplace_back(
            VlRtmdDataTypeRow::Atom{VlRtmdDataTypeRow::Atom::Kind::LOGIC, false, 1});
        m_hierarchy.emplace_back(VlRtmdHierRow::Push{
            "StorageModel", VlRtmdHierRow::Push::Kind::ROOT,
            VlRtmdHierRow::HierFlags::HAS_VARS | VlRtmdHierRow::HierFlags::HAS_TRACED_VARS});
        for (unsigned i = 0; i < widths.size(); ++i) {
            m_types.emplace_back(VlRtmdDataTypeRow::PackedArray{int(widths[i]) - 1, 0, 0, false});
            m_varTypes.emplace_back(VlRtmdVarTypeRow::Var{
                VlRtmdVarTypeRow::Var::Kind::VAR, VlRtmdVarTypeRow::Var::Direction::NONE, i + 1});
            const size_t offset = i * sizeof(m_storage.value[0]);
            for (unsigned kind = 0; kind < 4; ++kind) {
                const char* prefix = kind == 0 ? "s" : kind == 1 ? "alias" : kind == 2 ? "b" : "k";
                m_names.push_back(std::string{prefix} + std::to_string(widths[i]));
                const size_t addr
                    = (kind == 3 ? offsetof(Storage, known) : offsetof(Storage, value)) + offset;
                const size_t xzAddr
                    = kind == 3 ? VlRtmd::NOADDR
                                : (kind == 2 ? offsetof(Storage, otherXZ) : offsetof(Storage, xz))
                                      + offset;
                m_hierarchy.emplace_back(
                    VlRtmdHierRow::Var{m_names.back().c_str(), i, VlRtmd::NOIDX, addr,
                                       VlRtmdHierRow::VarFlags::IS_TRACED, xzAddr});
            }
        }
        m_hierarchy.emplace_back(VlRtmdHierRow::Pop{});
        m_types.emplace_back(VlRtmdDataTypeRow::End{});
        m_typeChunk = m_types.data();
        m_varTypeChunk = m_varTypes.data();
        m_hierChunk = m_hierarchy.data();
        VlRtmd* const rtmdp = new VlRtmd{};
        rtmdp->m_modelp = this;
        rtmdp->m_symsp = &m_storage;
        rtmdp->m_opt.m_trace = true;
        rtmdp->m_dataTypesTabpp = &m_typeChunk;
        rtmdp->m_varTypesTabpp = &m_varTypeChunk;
        rtmdp->m_hierTabpp = &m_hierChunk;
        rtmdp->m_chunkShift = 16;
        m_rtmdp = rtmdp;
        m_didInit = true;
        contextp()->addModel(this);
        for (unsigned i = 0; i < widths.size(); ++i) {
            const VlRtmdHierRow& a = m_hierarchy[1 + 4 * i];
            const VlRtmdHierRow& alias = m_hierarchy[2 + 4 * i];
            const VlRtmdHierRow& b = m_hierarchy[3 + 4 * i];
            if (rtmdp->varAddress(a) != rtmdp->varAddress(alias)
                || rtmdp->varAddress(a) != rtmdp->varAddress(b)
                || rtmdp->varXZAddress(a) != rtmdp->varXZAddress(alias)
                || rtmdp->varXZAddress(a) == rtmdp->varXZAddress(b)) {
                VL_FATAL_MT(__FILE__, __LINE__, "", "RTMD counterexample addresses differ");
            }
        }
    }
    void phase(unsigned phase) {
        m_storage = Storage{};
        for (unsigned i = 0; i < widths.size(); ++i) {
            for (unsigned bit = 0; bit < widths[i]; ++bit) {
                const unsigned state = (bit + phase) % 4;
                const EData mask = EData{1} << (bit % 32);
                if (state == 1 || state == 2) m_storage.value[i][bit / 32] |= mask;
                if (state >= 2)
                    m_storage.xz[i][bit / 32] |= mask;
                else
                    m_storage.otherXZ[i][bit / 32] |= mask;
                if ((bit + phase) % 2) m_storage.known[i][bit / 32] |= mask;
            }
        }
    }
};

template <typename Trace>
static void run(const char* filename, uint64_t closeTime) {
    VerilatedContext context;
    context.traceEverOn(true);
    StorageModel model{context};
    Trace trace;
    trace.contextp(&context);
    trace.set_time_unit("1ps");
    trace.set_time_resolution("1ps");
    trace.open(filename);
    const std::array<uint64_t, 5> times{{0, 3, 8, 15, 26}};
    for (unsigned phase = 0; phase < times.size(); ++phase) {
        model.phase(phase);
        context.time(times[phase]);
        trace.dump(times[phase]);
    }
    if (closeTime > 26) {
        context.time(closeTime);
        trace.dump(closeTime);
    }
    trace.close();
    trace.close();
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    run<VerilatedVcdC>(VL_STRINGIFY(TEST_OBJ_DIR) "/storage.vcd", 39);
    run<VerilatedFstC>(VL_STRINGIFY(TEST_OBJ_DIR) "/storage.fst", 39);
    run<VerilatedSaifC>(VL_STRINGIFY(TEST_OBJ_DIR) "/short.saif", 26);
    run<VerilatedSaifC>(VL_STRINGIFY(TEST_OBJ_DIR) "/long.saif", 39);
    std::printf("RTMD storage: widths=16 shared_value=16 distinct_xz=16 true_alias=16\n");
    std::printf("*-* All Finished *-*\n");
    return 0;
}
