// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// This program is free software; you can redistribute it and/or modify it
// under the terms of either the GNU Lesser General Public License Version 3
// or the Perl Artistic License Version 2.0.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
//*************************************************************************

#include "Vt_fourstate_vpi.h"
#include "verilated.h"
#include "verilated_vpi.h"

#include <memory>

// These require the above. Comment prevents clang-format moving them
#include "TestCheck.h"

int errors = 0;

static PLI_INT32 valueChanged(p_cb_data datap) {
    ++*reinterpret_cast<int*>(datap->user_data);
    return 0;
}

static void checkVector(vpiHandle handle, s_vpi_vecval* expectedp, int words) {
    s_vpi_value value{};
    value.format = vpiVectorVal;
    value.value.vector = expectedp;
    vpi_put_value(handle, &value, nullptr, vpiNoDelay);
    vpi_get_value(handle, &value);
    for (int i = 0; i < words; ++i) {
        TEST_CHECK_HEX_EQ(value.value.vector[i].aval, expectedp[i].aval);
        TEST_CHECK_HEX_EQ(value.value.vector[i].bval, expectedp[i].bval);
    }
}

int main(int argc, char** argv) {
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
    contextp->commandArgs(argc, argv);
    const std::unique_ptr<Vt_fourstate_vpi> topp{new Vt_fourstate_vpi{contextp.get(), "TOP"}};
    topp->eval();
    vpiHandle scalar = vpi_handle_by_name(const_cast<char*>("TOP.t.scalar"), nullptr);
    vpiHandle wide = vpi_handle_by_name(const_cast<char*>("TOP.t.wide"), nullptr);
    vpiHandle memory = vpi_handle_by_name(const_cast<char*>("TOP.t.memory"), nullptr);
    TEST_CHECK_NZ(scalar);
    TEST_CHECK_NZ(wide);
    TEST_CHECK_NZ(memory);
    if (errors) return 1;
    vpiHandle word = vpi_handle_by_index(memory, 2);
    TEST_CHECK_NZ(word);
    if (errors) return 1;

    int callbacks = 0;
    s_vpi_value callbackValue{};
    callbackValue.format = vpiVectorVal;
    s_cb_data callback{};
    callback.reason = cbValueChange;
    callback.cb_rtn = valueChanged;
    callback.obj = scalar;
    callback.value = &callbackValue;
    callback.user_data = reinterpret_cast<PLI_BYTE8*>(&callbacks);
    vpiHandle callbackHandle = vpi_register_cb(&callback);
    TEST_CHECK_NZ(callbackHandle);

    // Keep aval unchanged: the callback must notice a change in bval alone.
    s_vpi_vecval unknown[] = {{0, 0x7f}};
    checkVector(scalar, unknown, 1);
    VerilatedVpi::callValueCbs();
    TEST_CHECK_EQ(callbacks, 1);
    s_vpi_vecval known[] = {{0, 0}};
    checkVector(scalar, known, 1);
    VerilatedVpi::callValueCbs();
    TEST_CHECK_EQ(callbacks, 2);
    VerilatedVpi::callValueCbs();
    TEST_CHECK_EQ(callbacks, 2);

    s_vpi_vecval wideValue[] = {{0x12345678, 0x87654321}, {0xabcdef01, 0x10203040}, {1, 1}};
    checkVector(wide, wideValue, 3);
    s_vpi_vecval memoryValue[] = {{0x2468ace0, 0x13579bdf}, {0x1234, 0xabcd}};
    checkVector(word, memoryValue, 2);
    // vpi_remove_cb also releases its callback handle.
    vpi_remove_cb(callbackHandle);
    vpi_release_handle(word);
    vpi_release_handle(memory);
    vpi_release_handle(wide);
    vpi_release_handle(scalar);
    topp->final();
    if (errors) return 1;
    VL_PRINTF("*-* All Finished *-*\n");
    return 0;
}
