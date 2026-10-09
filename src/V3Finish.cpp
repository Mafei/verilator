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
// The jump stays within one generated function. Non-inlined functions, fork
// branches and expression-statement lambdas need separate
// termination propagation and are deliberately left unchanged. Exiting a
// source body does not bypass scheduler bookkeeping or cancel other regions.
// A separate early entry point handles one call-free final in the sole source
// top, before calls can be inlined. Other final protocols remain unchanged.
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
    const bool m_finalLocal = false;  // Early, separately qualified final body
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
    explicit FinishVisitor(AstFinal* nodep)
        : m_procp{nodep}
        , m_finalLocal{true} {
        iterateAndNextNull(nodep->stmtsp());
    }
    ~FinishVisitor() override {
        V3Stats::addStat(m_finalLocal ? "Finish, final local exits" : "Finish, source body exits",
                         m_statExits);
    }
};

// Inspect the original body before task inlining or expression lifting can
// erase a call boundary or introduce a local with a nontrivial lifetime.
class FinalLocalBodyVisitor final : public VNVisitorConst {
    bool m_blocked = false;
    bool m_hasFinish = false;

    void visit(const AstFinish*) override { m_hasFinish = true; }
    void visit(const AstNodeFTaskRef*) override { m_blocked = true; }
    void visit(const AstNodeCCall*) override { m_blocked = true; }
    void visit(const AstNodeFTask*) override { m_blocked = true; }
    void visit(const AstCFunc*) override { m_blocked = true; }
    void visit(const AstCExpr*) override { m_blocked = true; }
    void visit(const AstCExprUser*) override { m_blocked = true; }
    void visit(const AstCStmt*) override { m_blocked = true; }
    void visit(const AstCStmtUser*) override { m_blocked = true; }
    void visit(const AstCMethodHard*) override { m_blocked = true; }
    void visit(const AstCAwait*) override { m_blocked = true; }
    void visit(const AstCLocalScope*) override { m_blocked = true; }
    void visit(const AstDelay*) override { m_blocked = true; }
    void visit(const AstEventControl*) override { m_blocked = true; }
    void visit(const AstWait*) override { m_blocked = true; }
    void visit(const AstWaitFork*) override { m_blocked = true; }
    void visit(const AstFork*) override { m_blocked = true; }
    void visit(const AstExprStmt*) override { m_blocked = true; }
    void visit(const AstWith*) override { m_blocked = true; }
    void visit(const AstNewCopy*) override { m_blocked = true; }
    void visit(const AstNewDynamic*) override { m_blocked = true; }
    void visit(const AstUnlinkedRef*) override { m_blocked = true; }
    void visit(const AstParseRef*) override { m_blocked = true; }
    void visit(const AstMemberSel*) override { m_blocked = true; }
    void visit(const AstSystemT*) override { m_blocked = true; }
    void visit(const AstSystemF*) override { m_blocked = true; }
    void visit(const AstVar*) override { m_blocked = true; }
    void visit(const AstNodeVarRef* nodep) override {
        // Unresolved references can remain in dead code before elaboration.
        const AstVar* const varp = nodep->varp();
        const AstBasicDType* const dtypep
            = varp ? VN_CAST(varp->subDTypep(), BasicDType) : nullptr;
        if (!dtypep || !dtypep->isIntegralOrPacked()) m_blocked = true;
    }
    void visit(const AstNode* nodep) override { iterateChildrenConst(nodep); }

public:
    explicit FinalLocalBodyVisitor(const AstFinal* nodep) {
        iterateAndNextConstNull(nodep->stmtsp());
    }
    bool eligible() const { return m_hasFinish && !m_blocked; }
};

class FinalLocalScopeVisitor final : public VNVisitorConst {
    const AstNodeModule* m_modp = nullptr;
    const AstNode* m_parentp = nullptr;
    const AstNodeModule* m_finalModp = nullptr;
    const AstFinal* m_finalp = nullptr;
    bool m_finalDirect = false;
    unsigned m_topCount = 0;
    unsigned m_finalCount = 0;

    void visit(const AstNodeModule* nodep) override {
        VL_RESTORER(m_modp);
        VL_RESTORER(m_parentp);
        m_modp = nodep;
        m_parentp = nodep;
        if (nodep->isTop() && !VN_IS(nodep, Package) && !VN_IS(nodep, Class)) ++m_topCount;
        iterateChildrenConst(nodep);
    }
    void visit(const AstFinal* nodep) override {
        ++m_finalCount;
        m_finalp = nodep;
        m_finalModp = m_modp;
        m_finalDirect = m_parentp == m_modp;
    }
    void visit(const AstNode* nodep) override {
        VL_RESTORER(m_parentp);
        m_parentp = nodep;
        iterateChildrenConst(nodep);
    }

public:
    explicit FinalLocalScopeVisitor(const AstNetlist* nodep) { iterateConst(nodep); }
    const AstFinal* eligibleFinalp() const {
        // A source module with one final can have multiple runtime instances.
        // A generate can also clone one source final during elaboration. Require
        // a direct item of the sole source top to prove one runtime instance.
        const AstModule* const modp = VN_CAST(m_finalModp, Module);
        if (m_topCount != 1 || m_finalCount != 1 || !m_finalDirect || !modp || !modp->isTop()
            || modp->isProgram() || modp->isChecker()) {
            return nullptr;
        }
        return FinalLocalBodyVisitor{m_finalp}.eligible() ? m_finalp : nullptr;
    }
};

class FinalLocalRewriteVisitor final : public VNVisitor {
    const AstFinal* const m_finalp;

    void visit(AstFinal* nodep) override {
        if (nodep == m_finalp) FinishVisitor{nodep};
    }
    void visit(AstNode* nodep) override { iterateChildren(nodep); }

public:
    FinalLocalRewriteVisitor(AstNetlist* nodep, const AstFinal* finalp)
        : m_finalp{finalp} {
        iterate(nodep);
    }
};

void V3Finish::finishFinalLocalAll(AstNetlist* nodep) {
    UINFO(2, __FUNCTION__ << ":");
    if (const AstFinal* const finalp = FinalLocalScopeVisitor{nodep}.eligibleFinalp()) {
        FinalLocalRewriteVisitor{nodep, finalp};
    }
    V3Global::dumpCheckGlobalTree("finish-final-local", 0, dumpTreeEitherLevel() >= 3);
}

void V3Finish::finishAll(AstNetlist* nodep) {
    UINFO(2, __FUNCTION__ << ":");
    { FinishVisitor{nodep}; }
    V3Global::dumpCheckGlobalTree("finish", 0, dumpTreeEitherLevel() >= 3);
}
