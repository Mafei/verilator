// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

#include "verilated.h"
#include "verilated_types.h"
#include <cstdio>
#include <string>

int main() {
    static_assert(sizeof(VlUnpacked<IData, 2>) == 2 * sizeof(IData), "Array layout changed");
    static_assert(alignof(VlUnpacked<IData, 2>) == alignof(IData), "Array alignment changed");
    unsigned checks = 0;
    const auto check = [&checks](bool condition) {
        ++checks;
        return condition;
    };
    VlUnpacked<IData, 2> data{{11U, 22U}};
    IData first = 33U;
    IData second = 44U;
    const IData zero = 0U;
    IData& valid = data.atWriteBounded(true, 1U, first, zero);
    if (!check(&valid == &data[1])) return 1;
    valid = 55U;
    if (!check(data[1] == 55U)) return 1;
    for (unsigned repeat = 0; repeat < 4; ++repeat) {
        IData& left = data.atWriteBounded(false, 0xffffffffU, first, zero);
        IData& right = data.atWriteBounded(false, 2U, second, zero);
        if (!check(&left == &first && &right == &second && &left != &right)) return 1;
        if (!check(left == 0U && right == 0U)) return 1;
        left = 99U;
        right = 88U;
        if (!check(data[0] == 11U && data[1] == 55U)) return 1;
    }
    VlUnpacked<std::string, 2> words{{"left", "right"}};
    std::string fallback = "old";
    const std::string empty;
    for (unsigned repeat = 0; repeat < 4; ++repeat) {
        std::string& invalid = words.atWriteBounded(false, 20U, fallback, empty);
        if (!check(invalid.empty())) return 1;
        invalid = "changed";
        if (!check(words[0] == "left" && words[1] == "right")) return 1;
    }
    VlUnpacked<VlWide<3>, 2> wide{};
    VlWide<3> fallbackWide{};
    VlWide<3> allOnes{};
    allOnes[0] = 0xffffffffU;
    allOnes[1] = 0xffffffffU;
    allOnes[2] = 1U;
    for (unsigned repeat = 0; repeat < 4; ++repeat) {
        auto& invalid = wide.atWriteBounded(false, 30U, fallbackWide, allOnes);
        if (!check(invalid[0] == 0xffffffffU && invalid[1] == 0xffffffffU && invalid[2] == 1U)) return 1;
        invalid[0] = 0U;
    }
    if (checks != 26U) return 1;
    std::printf("BOUNDED_REF_CXX14_PASS checks=%u\n", checks);
    return 0;
}
