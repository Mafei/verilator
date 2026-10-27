// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
// Compare insertion APIs against an independent bit oracle, including canaries.
#include "verilated.h"

#include <climits>
#include <cstdio>

static_assert(__cplusplus == 201402L, "C++14 runtime required");

using Words = VlWide<10>;
static unsigned checks = 0;
static bool bit(const Words& words, int index) {
    return (words[1 + index / 32] >> (index % 32)) & 1U;
}
static void put(Words& words, int index, bool value) {
    const IData mask = IData{1} << (index % 32);
    IData& word = words[1 + index / 32];
    word = value ? word | mask : word & ~mask;
}
static Words initial(int width) {
    Words result{};
    for (int i = 0; i < 10; ++i) result[i] = 0xc0ffee11U;
    for (int index = 0; index < width; ++index) put(result, index, (index % 7) < 3);
    const int count = (width + 31) / 32;
    if (width % 32) result[count] &= (IData{1} << (width % 32)) - 1;
    return result;
}
static bool compare(const Words& got, const Words& expected, int width, int selected, int lsb,
                    int kind, bool alias) {
    ++checks;
    if (got == expected) return true;
    std::printf("FAIL width=%d selected=%d lsb=%d kind=%d alias=%d\n", width, selected, lsb, kind,
                alias);
    return false;
}
int main() {
    for (int width : {7, 15, 31, 33, 63, 65, 95, 129}) {
        for (int selected : {1, 3, 7, 31, 32, 33, 63, 64, 65, 95, 129}) {
            for (int lsb : {INT_MIN, -selected - 1, -selected, 1 - selected, -33, -17, -7, -2, -1,
                            0, 1, width - 2, width - 1, width, width + 1, INT_MAX}) {
                for (int kind = 0; kind < (width <= 32 ? 1 : width <= 64 ? 2 : 3); ++kind) {
                    for (int alias = 0; alias <= (width > 64 && kind == 2 && selected <= width);
                         ++alias) {
                        Words actual = initial(width);
                        Words expected = actual;
                        Words source{};
                        for (int index = 0; index < 8; ++index)
                            source[index + 1] = 0x96c35aa5U ^ (0x01234567U * index);
                        const QData scalar = kind == 0
                                                 ? QData{source[1]}
                                                 : QData{source[1]} | (QData{source[2]} << 32);
                        if (alias) source = actual;
                        const int sourceWidth = width <= 32 || kind == 0 ? 32
                                                : kind == 1              ? 64
                                                                         : selected;
                        for (int index = 0; index < selected; ++index) {
                            const int64_t target = static_cast<int64_t>(lsb) + index;
                            if (target >= 0 && target < width)
                                put(expected, static_cast<int>(target),
                                    index < sourceWidth && bit(source, index));
                        }
                        if (width <= 8) {
                            CData value = actual[1];
                            VL_ASSIGNSEL_II(width, selected, lsb, value,
                                            static_cast<IData>(scalar));
                            actual[1] = value;
                        } else if (width <= 16) {
                            SData value = actual[1];
                            VL_ASSIGNSEL_II(width, selected, lsb, value,
                                            static_cast<IData>(scalar));
                            actual[1] = value;
                        } else if (width <= 32) {
                            VL_ASSIGNSEL_II(width, selected, lsb, actual[1],
                                            static_cast<IData>(scalar));
                        } else if (width <= 64) {
                            QData value = QData{actual[1]} | (QData{actual[2]} << 32);
                            if (kind == 0)
                                VL_ASSIGNSEL_QI(width, selected, lsb, value,
                                                static_cast<IData>(scalar));
                            else
                                VL_ASSIGNSEL_QQ(width, selected, lsb, value, scalar);
                            actual[1] = static_cast<IData>(value);
                            actual[2] = static_cast<IData>(value >> 32);
                        } else if (kind == 0) {
                            VL_ASSIGNSEL_WI(width, selected, lsb, (WDataOutP{actual} + 1),
                                            static_cast<IData>(scalar));
                        } else if (kind == 1) {
                            VL_ASSIGNSEL_WQ(width, selected, lsb, (WDataOutP{actual} + 1), scalar);
                        } else {
                            VL_ASSIGNSEL_WW(width, selected, lsb, (WDataOutP{actual} + 1),
                                            (WDataInP{alias ? actual : source} + 1));
                        }
                        if (!compare(actual, expected, width, selected, lsb, kind, alias))
                            return 1;
                    }
                }
            }
        }
    }
    std::printf("CXX14_INSERT_PASS checks=%u\n", checks);
    return 0;
}
