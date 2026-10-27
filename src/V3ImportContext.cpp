// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// DESCRIPTION: Capture top-level parser descriptions and their raw AST order.
//   The parser reports descriptions in their original interleaving, before
//   LinkParse moves declarations. The diagnostic ledger stores only values;
//   it neither resolves names nor attaches bindings to clones. Raw AST preorder
//   is recorded explicitly, rather than presented as a completed lexical binder.
//
// Code available from: https://verilator.org
//
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
//*************************************************************************

#include "V3PchAstNoMT.h"  // VL_MT_DISABLED_CODE_UNIT

#include "V3ImportContext.h"

#include "V3File.h"
#include "V3Global.h"

VL_DEFINE_DEBUG_FUNCTIONS;

class ImportContextCaptureVisitor final : public VNVisitorConst {
    V3ImportContext& m_context;
    int m_scope = 1;
    int m_parentScope = 0;
    int m_parentCut = 0;

    void record(const AstNode* const nodep, const char* const kind,
                const std::string& package = "") {
        m_context.m_events.push_back(V3ImportContext::Event{
            m_scope, m_parentScope, m_parentCut, kind, nodep->typeName(), nodep->name(), package});
    }

    void visit(AstNode* nodep) override {
        // Record every syntax node, including roles that a future binder must
        // distinguish from an eligible unqualified name use.
        const bool scope = VN_IS(nodep, NodeModule) || VN_IS(nodep, NodeFTask)
                           || VN_IS(nodep, NodeBlock) || VN_IS(nodep, GenBlock)
                           || VN_IS(nodep, NodeForeach);
        if (scope) {
            VL_RESTORER(m_scope);
            VL_RESTORER(m_parentScope);
            VL_RESTORER(m_parentCut);
            m_parentScope = m_scope;
            m_parentCut = static_cast<int>(m_context.m_events.size()) - 1;
            m_scope = ++m_context.m_nextScope;
            record(nodep, "ENTER_SCOPE");
            iterateChildrenConst(nodep);
            record(nodep, "LEAVE_SCOPE");
        } else if (const AstPackageImport* const impp = VN_CAST(nodep, PackageImport)) {
            record(nodep, "IMPORT", impp->pkgName());
            iterateChildrenConst(nodep);
        } else if (const AstPackageExport* const expp = VN_CAST(nodep, PackageExport)) {
            record(nodep, "EXPORT", expp->pkgName());
            iterateChildrenConst(nodep);
        } else if (VN_IS(nodep, PackageExportStarStar)) {
            record(nodep, "EXPORT_ALL");
            iterateChildrenConst(nodep);
        } else {
            record(nodep, "SYNTAX");
            iterateChildrenConst(nodep);
        }
    }

public:
    ImportContextCaptureVisitor(V3ImportContext& context, AstNode* const nodep, const bool list)
        : m_context{context} {
        if (list) {
            iterateAndNextConstNull(nodep);
        } else {
            iterateConst(nodep);
        }
    }
};

void V3ImportContext::capture(AstNode* const nodep, const bool list) {
    if (debug() < 3 || !nodep) return;
    if (m_events.empty()) {
        m_events.push_back(Event{1, 0, 0, "ENTER_SCOPE", "UNIT", "$unit", ""});
    }
    const ImportContextCaptureVisitor visitor{*this, nodep, list};
}

void V3ImportContext::dump() const {
    if (debug() < 3) return;
    V3OutJsonFile of{v3Global.opt.hierTopDataDir() + "/" + v3Global.opt.prefix()
                     + "__import_context.json"};
    of.put("schema", "import-context-capture-v1");
    of.put("bindingsProvided", false);
    of.put("cloneBindingsProvided", false);
    of.put("queryRolesClassified", false);
    of.put("order", "parser-description/raw-AST-preorder");
    of.put("syntheticImportsCaptured", false);
    of.begin("events", '[');
    int ordinal = 0;
    for (const Event& event : m_events) {
        of.begin();
        of.put("ordinal", ordinal++);
        of.put("scope", event.scope);
        of.put("parentScope", event.parentScope);
        of.put("parentCut", event.parentCut);
        of.put("kind", event.kind);
        of.put("nodeType", event.nodeType);
        of.put("name", event.name);
        of.put("package", event.package);
        of.end();
    }
    of.end();
}
