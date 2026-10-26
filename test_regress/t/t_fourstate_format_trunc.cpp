// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

#include "verilated.h"
#include "verilated_funcs.h"

#include <algorithm>
#include <array>
#include <cstdio>
#include <string>

static unsigned checks = 0;
static unsigned failures = 0;

static void check(bool okay, const char* namep, int api, const char* kindp) {
    ++checks;
    VL_PRINTF("PACKED_TRUNC_RUNTIME_CHECK n=%u case=%s api=%s kind=%s got=%d expected=1\n",
              checks, namep, api ? "string" : "char", kindp, okay ? 1 : 0);
    if (!okay) ++failures;
}

template <typename T> struct GuardedScalar final {
    std::array<CData, 8> before;
    T value;
    std::array<CData, 8> after;
};

template <size_t N> struct GuardedWide final {
    std::array<CData, 8> before;
    std::array<EData, N> value;
    std::array<CData, 8> after;
};

template <typename T> static bool canaries(const T& guarded) {
    return std::all_of(guarded.before.begin(), guarded.before.end(),
                       [](CData byte) { return byte == 0xa5; })
           && std::all_of(guarded.after.begin(), guarded.after.end(),
                          [](CData byte) { return byte == 0xa5; });
}

template <typename T>
static void scalarCase(const char* namep, int bits, const char* textp, QData expected) {
    for (int api = 0; api != 2; ++api) {
        GuardedScalar<T> guarded{};
        guarded.before.fill(0xa5);
        guarded.after.fill(0xa5);
        guarded.value = static_cast<T>(VL_MASK_Q(bits));
        if (api) {
            VL_SFORMAT_NX(bits, guarded.value, std::string{textp}, 0);
        } else {
            VL_SFORMAT_NX(bits, guarded.value, textp, 0);
        }
        check(static_cast<QData>(guarded.value) == expected, namep, api, "value");
        check(canaries(guarded), namep, api, "canary");
    }
}

template <size_t N>
static void wideCase(const char* namep, int bits, const char* textp,
                     const std::array<EData, N>& expected) {
    for (int api = 0; api != 2; ++api) {
        GuardedWide<N> guarded{};
        guarded.before.fill(0xa5);
        guarded.after.fill(0xa5);
        guarded.value.fill(0xffffffffU);
        guarded.value[N - 1] &= VL_MASK_E(bits);
        if (api) {
            VL_SFORMAT_NX(bits, guarded.value.data(), std::string{textp}, 0);
        } else {
            VL_SFORMAT_NX(bits, guarded.value.data(), textp, 0);
        }
        check(guarded.value == expected, namep, api, "value");
        check(canaries(guarded), namep, api, "canary");
    }
}

int main(int argc, char** argv) {
    VerilatedContext context;
    context.commandArgs(argc, argv);

    // These literal values do not reuse a production packing or formatting helper.
    scalarCase<CData>("byte_empty", 8, "", 0x0ULL);
    scalarCase<CData>("byte_exact", 8, "A", 0x41ULL);
    scalarCase<CData>("byte_long", 8, "ZA", 0x41ULL);
    scalarCase<CData>("bit7_high", 7, "\xff", 0x7fULL);
    scalarCase<SData>("half_empty", 16, "", 0x0ULL);
    scalarCase<SData>("half_short", 16, "A", 0x41ULL);
    scalarCase<SData>("half_exact", 16, "AB", 0x4142ULL);
    scalarCase<SData>("half_long", 16, "ZAB", 0x4142ULL);
    scalarCase<SData>("bit9_exact", 9, "AB", 0x142ULL);
    scalarCase<SData>("bit15_high", 15, "\xff" "B", 0x7f42ULL);
    scalarCase<IData>("word_empty", 32, "", 0x0ULL);
    scalarCase<IData>("word_short", 32, "A", 0x41ULL);
    scalarCase<IData>("word_exact", 32, "ABCD", 0x41424344ULL);
    scalarCase<IData>("word_long", 32, "ZABCD", 0x41424344ULL);
    scalarCase<IData>("bit17_long", 17, "ABCD", 0x4344ULL);
    scalarCase<IData>("bit29_exact", 29, "ABCD", 0x01424344ULL);
    scalarCase<QData>("quad_empty", 64, "", 0x0ULL);
    scalarCase<QData>("quad_short", 64, "A", 0x41ULL);
    scalarCase<QData>("quad_exact", 64, "ABCDEFGH", 0x4142434445464748ULL);
    scalarCase<QData>("quad_long", 64, "ZABCDEFGH", 0x4142434445464748ULL);
    scalarCase<QData>("bit33_long", 33, "ZACDEF", 0x143444546ULL);
    scalarCase<QData>("bit63_high", 63, "\xff" "BCDEFGH", 0x7f42434445464748ULL);

    wideCase<3>("wide65_empty", 65, "", {{0, 0, 0}});
    wideCase<3>("wide65_short", 65, "A", {{0x41, 0, 0}});
    wideCase<3>("wide65_exact", 65, "ABCDEFGHI", {{0x46474849, 0x42434445, 1}});
    wideCase<3>("wide65_long", 65, "ZABCDEFGHI", {{0x46474849, 0x42434445, 1}});
    wideCase<3>("wide95_empty", 95, "", {{0, 0, 0}});
    wideCase<3>("wide95_short", 95, "A", {{0x41, 0, 0}});
    wideCase<3>("wide95_exact", 95, "ABCDEFGHIJKL", {{0x494a4b4c, 0x45464748, 0x41424344}});
    wideCase<3>("wide95_long", 95, "ZABCDEFGHIJKL", {{0x494a4b4c, 0x45464748, 0x41424344}});
    wideCase<3>("wide95_high", 95, "\xff" "BCDEFGHIJKL", {{0x494a4b4c, 0x45464748, 0x7f424344}});
    wideCase<5>("wide129_empty", 129, "", {{0, 0, 0, 0, 0}});
    wideCase<5>("wide129_short", 129, "A", {{0x41, 0, 0, 0, 0}});
    wideCase<5>("wide129_exact", 129, "ABCDEFGHIJKLMNOPQ",
                {{0x4e4f5051, 0x4a4b4c4d, 0x46474849, 0x42434445, 1}});
    wideCase<5>("wide129_long", 129, "ZABCDEFGHIJKLMNOPQ",
                {{0x4e4f5051, 0x4a4b4c4d, 0x46474849, 0x42434445, 1}});
    wideCase<5>("wide129_high", 129, "\xfe" "BCDEFGHIJKLMNOPQ",
                {{0x4e4f5051, 0x4a4b4c4d, 0x46474849, 0x42434445, 0}});

    for (int api = 0; api != 2; ++api) {
        std::string output = "seed";
        if (api) VL_SFORMAT_NX(output, std::string{"ZABCD"}, 0);
        else VL_SFORMAT_NX(output, "ZABCD", 0);
        check(output == "ZABCD", "unpacked_string", api, "value");
    }
    if (checks != 146 || failures) {
        VL_PRINTF("%%Error: packed truncation checks=%u failures=%u\n", checks, failures);
        return 1;
    }
    VL_PRINTF("PACKED_TRUNC_RUNTIME_PASS checks=146\n*-* All Finished *-*\n");
    return 0;
}
