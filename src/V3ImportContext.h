// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// DESCRIPTION: Capture parser descriptions before linker AST reordering.
//
// Code available from: https://verilator.org
//
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
//*************************************************************************

#ifndef VERILATOR_V3IMPORTCONTEXT_H_
#define VERILATOR_V3IMPORTCONTEXT_H_

#include "config_build.h"
#include "verilatedos.h"

#include <string>
#include <vector>

class AstNode;
class ImportContextCaptureVisitor;

// Capture-only source history. It supplies no name bindings to the linker.
class V3ImportContext final {
    friend class ImportContextCaptureVisitor;

    struct Event final {
        int scope;
        int parentScope;
        int parentCut;
        std::string kind;
        std::string nodeType;
        std::string name;
        std::string package;
    };

    // Value records deliberately retain no AST, FileLine, or VSymEnt pointers.
    std::vector<Event> m_events;
    int m_nextScope = 1;  // Scope one is the parser's shared compilation unit

public:
    V3ImportContext() = default;
    void capture(AstNode* nodep, bool list) VL_MT_DISABLED;
    void dump() const VL_MT_DISABLED;
};

#endif  // guard
