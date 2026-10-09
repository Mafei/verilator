// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// DESCRIPTION: Verilator: End source process bodies after $finish
//
// Code available from: https://verilator.org
//
//*************************************************************************
//
// This program is free software; you can redistribute it and/or modify it
// under the terms of either the GNU Lesser General Public License Version 3
// or the Perl Artistic License Version 2.0.
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
//
//*************************************************************************
// Run after task inlining, while each initial/always still owns its source
// body. Wrap only bodies containing $finish in a jump block, then leave that
// block immediately after requesting termination. This also skips the caller's
// remaining statements and copyback after an inlined finishing call.
//
// The jump stays within one generated function. Final blocks, non-inlined
// functions, fork branches and expression-statement lambdas need separate
// termination propagation and are deliberately left unchanged. Exiting a
// source body does not bypass scheduler bookkeeping or cancel other regions.
//*************************************************************************

#include "V3PchAstNoMT.h"  // VL_MT_DISABLED_CODE_UNIT

#include "V3Finish.h"

#include "V3Stats.h"

VL_DEFINE_DEBUG_FUNCTIONS;

class FinishVisitor final : public VNVisitor {
    // NODE STATE
    //  AstNodeProcedure::user1p() -> AstJumpBlock*, exit for this source body
    //  AstFinish::user2()         -> bool, processed
    const VNUser1InUse m_user1InUse;
    const VNUser2InUse m_user2InUse;

    // STATE
    AstNodeProcedure* m_procp = nullptr;  // Current supported source process
    VDouble0 m_statExits;  // Source-body exits added

    AstJumpBlock* getExitBlock() {
        if (m_procp->user1p()) return VN_AS(m_procp->user1p(), JumpBlock);
        AstNode* const bodyp = m_procp->stmtsp();
        UASSERT_OBJ(bodyp, m_procp, "Finish outside a source process body");
        VNRelinker relinker;
        bodyp->unlinkFrBackWithNext(&relinker);
        AstJumpBlock* const blockp = new AstJumpBlock{m_procp->fileline(), bodyp};
        relinker.relink(blockp);
        m_procp->user1p(blockp);
        return blockp;
    }

    void visit(AstNodeProcedure* nodep) override {
        VL_RESTORER(m_procp);
        m_procp = (VN_IS(nodep, Initial) || VN_IS(nodep, Always)) ? nodep : nullptr;
        // Sensitivity expressions are not part of the source body.
        iterateAndNextNull(nodep->stmtsp());
    }
    // These boundaries have separate generated functions or return types.
    void visit(AstCFunc*) override {}
    void visit(AstNodeFTask*) override {}
    void visit(AstFork*) override {}
    void visit(AstExprStmt*) override {}
    void visit(AstWith*) override {}
    void visit(AstFinish* nodep) override {
        if (!m_procp || nodep->user2SetOnce()) return;
        AstJumpBlock* const blockp = getExitBlock();
        nodep->addNextHere(new AstJumpGo{nodep->fileline(), blockp});
        ++m_statExits;
    }
    void visit(AstNode* nodep) override { iterateChildren(nodep); }

public:
    explicit FinishVisitor(AstNetlist* nodep) { iterate(nodep); }
    ~FinishVisitor() override { V3Stats::addStat("Finish, source body exits", m_statExits); }
};

void V3Finish::finishAll(AstNetlist* nodep) {
    UINFO(2, __FUNCTION__ << ":");
    { FinishVisitor{nodep}; }
    V3Global::dumpCheckGlobalTree("finish", 0, dumpTreeEitherLevel() >= 3);
}
