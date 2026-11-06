// DESCRIPTION: Verilator: Wide-source scalar clipping boundary matrix
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

#include "verilated.h"

#include <cstdio>
#include <limits>

static const int s_offsets[] = {std::numeric_limits<int>::min(),
                                -200,
                                -97,
                                -96,
                                -95,
                                -66,
                                -65,
                                -64,
                                -63,
                                -34,
                                -33,
                                -32,
                                -31,
                                -4,
                                -3,
                                -2,
                                -1,
                                0,
                                1,
                                2,
                                3,
                                4,
                                15,
                                30,
                                31,
                                32,
                                33,
                                62,
                                63,
                                64,
                                95,
                                std::numeric_limits<int>::max()};
static unsigned s_checks = 0;

static QData mask(int bits) { return bits == 64 ? ~QData{0} : (QData{1} << bits) - 1; }

static EData pattern(unsigned id, unsigned word) {
    if (id == 0) return 0;
    if (id == 1) return ~EData{0};
    if (id == 2) return word & 1U ? 0xaaaaaaaaU : 0x55555555U;
    return 0x9e3779b9U * (word + 1U) ^ 0x635a5c87U;
}

// Independent per-destination-bit oracle, with no clipping/shift helper reuse.
template <typename T_Read>
static QData oracle(QData old, int rbits, int obits, int lsb, T_Read readWord) {
    QData expected = old;
    for (int bit = 0; bit < rbits; ++bit) {
        const int64_t sourceBit = static_cast<int64_t>(bit) - lsb;
        if (sourceBit < 0 || sourceBit >= obits) continue;
        const QData bitMask = QData{1} << bit;
        if ((readWord(static_cast<unsigned>(sourceBit / 32)) >> (sourceBit & 31)) & 1U) {
            expected |= bitMask;
        } else {
            expected &= ~bitMask;
        }
    }
    return expected;
}

static bool check(const char* family, int rbits, int obits, int lsb, unsigned patternId,
                  QData actual, QData expected) {
    ++s_checks;
    if (actual == expected) return true;
    std::fprintf(stderr,
                 "%%Error: %s rbits=%d obits=%d lsb=%d pattern=%u got=%llx expected=%llx\n",
                 family, rbits, obits, lsb, patternId, static_cast<unsigned long long>(actual),
                 static_cast<unsigned long long>(expected));
    return false;
}

template <typename T_Dest>
static bool matrix_iq(int rbits, int obits) {
    for (unsigned p = 0; p < 4; ++p) {
        const QData rhs = QData{pattern(p, 0)} | (QData{pattern(p, 1)} << 32);
        const QData initial = (0x635aa5c796b4de81ULL ^ rhs) & mask(rbits);
        for (int lsb : s_offsets) {
            T_Dest actual = static_cast<T_Dest>(initial);
            const QData expected = oracle(initial, rbits, obits, lsb, [rhs](unsigned word) {
                return word < 2 ? static_cast<EData>(rhs >> (word * 32)) : EData{0};
            });
            // Match emitted constants such as 0xffffffffU. The existing runtime
            // index API is int; the oracle keeps the corresponding signed value.
            VL_ASSIGNSEL_IQ(rbits, obits, static_cast<IData>(lsb), actual, rhs);
            if (!check("IQ", rbits, obits, lsb, p, actual, expected)) return false;
        }
    }
    return true;
}

template <typename T_Dest>
struct WideCall {
    static void call(int rbits, int obits, IData indexBits, T_Dest& dest, WDataInP rhs) {
        VL_ASSIGNSEL_IW(rbits, obits, indexBits, dest, rhs);
    }
    static const char* name() { return "IW"; }
};
template <>
struct WideCall<QData> {
    static void call(int rbits, int obits, IData indexBits, QData& dest, WDataInP rhs) {
        VL_ASSIGNSEL_QW(rbits, obits, indexBits, dest, rhs);
    }
    static const char* name() { return "QW"; }
};

template <typename T_Dest, int OBITS>
static bool matrix_wide(int rbits) {
    constexpr int WORDS = (OBITS + 31) / 32;
    for (unsigned p = 0; p < 4; ++p) {
        VlWide<WORDS> rhs;
        for (int word = 0; word < WORDS; ++word) rhs[word] = pattern(p, word);
        // Padding bits above OBITS are deliberately dirty and must not leak.
        const QData initial = (0x635aa5c796b4de81ULL ^ pattern(p, 0)) & mask(rbits);
        for (int lsb : s_offsets) {
            T_Dest actual = static_cast<T_Dest>(initial);
            const QData expected = oracle(initial, rbits, OBITS, lsb, [&rhs](unsigned word) {
                return word < WORDS ? rhs[word] : EData{0};
            });
            WideCall<T_Dest>::call(rbits, OBITS, static_cast<IData>(lsb), actual, rhs);
            if (!check(WideCall<T_Dest>::name(), rbits, OBITS, lsb, p, actual, expected)) {
                return false;
            }
        }
    }
    return true;
}

template <typename T_Dest>
static bool scalar_destination(int rbits) {
    return matrix_iq<T_Dest>(rbits, 33) && matrix_iq<T_Dest>(rbits, 63)
           && matrix_iq<T_Dest>(rbits, 64) && matrix_wide<T_Dest, 65>(rbits)
           && matrix_wide<T_Dest, 95>(rbits) && matrix_wide<T_Dest, 97>(rbits);
}

int main() {
    if (!scalar_destination<CData>(4) || !scalar_destination<SData>(15)
        || !scalar_destination<IData>(31) || !scalar_destination<IData>(32)
        || !matrix_wide<QData, 65>(63) || !matrix_wide<QData, 95>(63)
        || !matrix_wide<QData, 97>(63) || !matrix_wide<QData, 65>(64)
        || !matrix_wide<QData, 95>(64) || !matrix_wide<QData, 97>(64))
        return 10;
    if (s_checks != 3840) return 11;
    std::printf("Clipped scalar runtime checks: %u\n", s_checks);
    std::puts("*-* All Finished *-*");
    return 0;
}
