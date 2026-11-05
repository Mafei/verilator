// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// DESCRIPTION: Verilator: Public DPI helpers for CCall output regression
//
// This file ONLY is placed under the Creative Commons Public Domain.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: CC0-1.0
//*************************************************************************

#include "svdpi.h"

#include <cstring>

#include VM_PREFIX_INCLUDE_DPI

static int s_contextCalls = 0;
static int s_contextOk = 0;
static int s_emptyCalls = 0;

int ccall_seed(int index) { return ((index * 37) % 251) - 125; }

int ccall_pair(int first, int second) { return first * 101 + second; }

int ccall_context_pair(int first, int second) {
    ++s_contextCalls;
    const svScope scope = svGetScope();
    const svScope declarationScope = svGetScopeFromName("TOP.t");
    const char* filenamep = nullptr;
    int line = 0;
    s_contextOk = scope && declarationScope && scope == declarationScope
                  && svGetCallerInfo(&filenamep, &line) && filenamep && line > 0
                  && std::strstr(filenamep, "t_debug_emitv_ccall.v");
    return first * 103 - second;
}

int ccall_context_ok() { return s_contextOk; }

int ccall_context_count() { return s_contextCalls; }

int ccall_single(int value) { return value - 19; }

int ccall_empty() { return 17; }

int ccall_empty_task() {
    ++s_emptyCalls;
    return 0;
}

int ccall_empty_count() { return s_emptyCalls; }
