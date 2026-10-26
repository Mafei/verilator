// DESCRIPTION: Verilator: Late-declared swaps and restorer lifetime checks
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0

// Keep the common header before the types whose swap overloads it must find.
#include "verilatedos.h"

#include <array>
#include <cstdio>
#include <map>
#include <tuple>
#include <vector>

namespace {
int checks = 0;
int failures = 0;

void check(bool condition, const char* typep, const char* phasep) {
    ++checks;
    if (!condition) {
        ++failures;
        std::printf("RESTORER_CLEAR failed type=%s phase=%s\n", typep, phasep);
    }
}

template <typename T>
void exercise(const T& original, const T& replacement, const char* typep) {
    T value = original;
    {
        VL_RESTORER_CLEAR(value);
        check(value == T{}, typep, "clear");
        check(VL_RESTORER_PREV(value) == original, typep, "saved");
        value = replacement;
        check(VL_RESTORER_PREV(value) == original, typep, "saved-after-write");
    }
    check(value == original, typep, "restore");
    T empty{};
    {
        VL_RESTORER_CLEAR(empty);
        check(empty == T{}, typep, "default-clear");
        check(VL_RESTORER_PREV(empty) == T{}, typep, "default-saved");
        empty = replacement;
    }
    check(empty == T{}, typep, "default-restore");
}

// No associated swap: the ordinary std::swap fallback must still work.
struct Fallback final {
    int value = 0;
    explicit Fallback(int initial = 0)
        : value{initial} {}
    Fallback(const Fallback&) = default;
    Fallback(Fallback&&) = default;
    Fallback& operator=(const Fallback&) = default;
    Fallback& operator=(Fallback&&) = default;
    ~Fallback() {}  // A non-trivial type is required by VRestorerClear.
};

bool operator==(const Fallback& lhs, const Fallback& rhs) { return lhs.value == rhs.value; }
}  // namespace

// Declared after verilatedos.h and usable only through its associated swap.
namespace late_adl {
int swaps = 0;
struct State final {
    int value = 0;
    explicit State(int initial = 0)
        : value{initial} {}
    State(const State&) = delete;
    State(State&&) = delete;
    State& operator=(const State&) = delete;
    State& operator=(State&&) = delete;
    ~State() {}
};

void swap(State& lhs, State& rhs) noexcept {
    std::swap(lhs.value, rhs.value);
    ++swaps;
}
}  // namespace late_adl

int main() {
    using Array = std::array<std::map<int, std::vector<int>>, 2>;
    Array array;
    array[0][3] = {5, 7};
    array[1][-2] = {11};
    Array arrayReplacement;
    arrayReplacement[1][19] = {23, 29};
    exercise(array, arrayReplacement, "array");

    using Tuple = std::tuple<std::vector<int>, std::map<int, int>>;
    Tuple tuple;
    std::get<0>(tuple) = {31, 37};
    std::get<1>(tuple)[41] = 43;
    Tuple tupleReplacement;
    std::get<0>(tupleReplacement) = {47};
    exercise(tuple, tupleReplacement, "tuple");
    exercise(Fallback{53}, Fallback{59}, "fallback");

    late_adl::State value{61};
    int before = late_adl::swaps;
    {
        const VRestorerClear<late_adl::State> restorer{value};
        check(value.value == 0, "adl", "clear");
        check(restorer.saved().value == 61, "adl", "saved");
        check(late_adl::swaps == before + 1, "adl", "constructor-swap");
        value.value = 67;
        check(restorer.saved().value == 61, "adl", "saved-after-write");
    }
    check(value.value == 61, "adl", "restore");
    check(late_adl::swaps == before + 2, "adl", "destructor-swap");

    late_adl::State empty;
    before = late_adl::swaps;
    {
        const VRestorerClear<late_adl::State> restorer{empty};
        check(empty.value == 0, "adl", "default-clear");
        check(restorer.saved().value == 0, "adl", "default-saved");
        check(late_adl::swaps == before + 1, "adl", "default-constructor-swap");
        empty.value = 71;
        check(restorer.saved().value == 0, "adl", "default-saved-after-write");
    }
    check(empty.value == 0, "adl", "default-restore");
    check(late_adl::swaps == before + 2, "adl", "default-destructor-swap");

    std::printf("RESTORER_CLEAR checks=%d failures=%d\n", checks, failures);
    if (failures) return 1;
    std::printf("*-* All Finished *-*\n");
    return 0;
}
