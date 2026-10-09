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
// Internal source tasks also get local exits. A direct statement call to a
// finishing task checks the termination request before output copyback or
// further source statements. Timing later changes these calls into awaits,
// keeping the check after resumption. Calls from final, fork, expression
// lambdas and other unsupported boundaries exclude the shared task and its
// callees from this transformation. Exiting a source body does not bypass
// scheduler bookkeeping or cancel other regions.
// A separate early entry point qualifies original call-free final bodies,
// before calls can be inlined. Scheduling connects their local exits to a
// model-local flag that stops the remaining final bodies during evalFinal.
// Finals with calls or locals retain their existing internal behavior.
//*************************************************************************

#include "V3PchAstNoMT.h"  // VL_MT_DISABLED_CODE_UNIT

#include "V3Finish.h"

#include "V3Graph.h"
#include "V3Stats.h"

#include <queue>

VL_DEFINE_DEBUG_FUNCTIONS;

class FinishVertex final : public V3GraphVertex {
    VL_RTTI_IMPL(FinishVertex, V3GraphVertex);
    const bool m_canExit;  // Supported source process or internal source task
    bool m_blocked;  // Reachable from an unsupported call boundary
    bool m_hasFinish = false;  // Directly or transitively requests termination

public:
    FinishVertex(V3Graph* graphp, bool canExit)
        : V3GraphVertex{graphp}
        , m_canExit{canExit}
        , m_blocked{!canExit} {}
    bool canExit() const { return m_canExit; }
    bool blocked() const { return m_blocked; }
    void blocked(bool flag) { m_blocked = flag; }
    bool hasFinish() const { return m_hasFinish; }
    void hasFinish(bool flag) { m_hasFinish = flag; }
};

// Resolve the shared-task boundary before rewriting any bodies. A final may
// call the same task as an initial while gotFinish is already set, so excluding
// just the final call site would not protect checks inside the shared task.
class FinishTaskStateVisitor final : public VNVisitorConst {
    V3Graph m_callGraph;  // Edges point from source caller to callee
    std::map<const AstNode*, FinishVertex*> m_vertexps;  // Source body vertices
    FinishVertex* m_vxp = nullptr;  // Source body owning the current node
    const AstCCall* m_directCallp = nullptr;  // Call that owns a statement
    bool m_allowExit = false;  // Within one supported source body

    static bool eligibleTask(const AstCFunc* nodep) {
        return nodep->sourceTask() && nodep->rtnTypeVoid() == "void" && !nodep->funcPublic()
               && !nodep->dpiContext() && !nodep->dpiExportDispatcher() && !nodep->dpiExportImpl()
               && !nodep->dpiImportPrototype() && !nodep->dpiImportWrapper()
               && !nodep->isConstructor() && !nodep->isDestructor() && !nodep->isVirtual()
               && !VN_IS(nodep->scopep()->modp(), Class) && !VN_IS(nodep->scopep()->modp(), Iface);
    }
    FinishVertex* getVertex(const AstNode* nodep) {
        const auto it = m_vertexps.find(nodep);
        if (it != m_vertexps.end()) return it->second;
        const AstCFunc* const funcp = VN_CAST(nodep, CFunc);
        const bool canExit
            = funcp ? eligibleTask(funcp) : (VN_IS(nodep, Initial) || VN_IS(nodep, Always));
        FinishVertex* const vxp = new FinishVertex{&m_callGraph, canExit};
        m_vertexps.emplace(nodep, vxp);
        return vxp;
    }
    void iterateBoundary(AstNode* nodep) {
        VL_RESTORER(m_allowExit);
        m_allowExit = false;
        iterateChildrenConst(nodep);
    }
    void propagateBlocked() {
        std::queue<FinishVertex*> work;
        for (V3GraphVertex& vtx : m_callGraph.vertices()) {
            FinishVertex* const vxp = vtx.as<FinishVertex>();
            if (vxp->blocked()) work.push(vxp);
        }
        while (!work.empty()) {
            FinishVertex* const callerp = work.front();
            work.pop();
            for (V3GraphEdge& edge : callerp->outEdges()) {
                FinishVertex* const calleep = edge.top()->as<FinishVertex>();
                if (calleep->blocked()) continue;
                calleep->blocked(true);
                work.push(calleep);
            }
        }
    }
    void propagateFinish() {
        std::queue<FinishVertex*> work;
        for (V3GraphVertex& vtx : m_callGraph.vertices()) {
            FinishVertex* const vxp = vtx.as<FinishVertex>();
            if (!vxp->blocked() && vxp->hasFinish()) work.push(vxp);
        }
        while (!work.empty()) {
            FinishVertex* const calleep = work.front();
            work.pop();
            for (V3GraphEdge& edge : calleep->inEdges()) {
                FinishVertex* const callerp = edge.fromp()->as<FinishVertex>();
                if (callerp->blocked() || callerp->hasFinish()) continue;
                callerp->hasFinish(true);
                work.push(callerp);
            }
        }
    }

    void visit(AstNodeProcedure* nodep) override {
        VL_RESTORER(m_vxp);
        VL_RESTORER(m_allowExit);
        m_vxp = getVertex(nodep);
        m_allowExit = m_vxp->canExit();
        iterateAndNextConstNull(nodep->stmtsp());
    }
    void visit(AstCFunc* nodep) override {
        VL_RESTORER(m_vxp);
        VL_RESTORER(m_allowExit);
        m_vxp = getVertex(nodep);
        m_allowExit = m_vxp->canExit();
        iterateChildrenConst(nodep);
    }
    void visit(AstStmtExpr* nodep) override {
        VL_RESTORER(m_directCallp);
        m_directCallp = VN_CAST(nodep->exprp(), CCall);
        iterateChildrenConst(nodep);
    }
    void visit(AstNodeCCall* nodep) override {
        AstCFunc* const funcp = nodep->funcp();
        UASSERT_OBJ(funcp, nodep, "Call has no resolved CFunc");
        FinishVertex* const calleep = getVertex(funcp);
        if (m_vxp) new V3GraphEdge{&m_callGraph, m_vxp, calleep, 1};
        if (!m_vxp || !m_allowExit || nodep != m_directCallp) calleep->blocked(true);
        iterateChildrenConst(nodep);
    }
    void visit(AstFinish*) override {
        if (m_vxp && m_allowExit) m_vxp->hasFinish(true);
    }
    void visit(AstNodeFTask* nodep) override { iterateBoundary(nodep); }
    void visit(AstFork* nodep) override { iterateBoundary(nodep); }
    void visit(AstExprStmt* nodep) override { iterateBoundary(nodep); }
    void visit(AstWith* nodep) override { iterateBoundary(nodep); }
    void visit(AstNode* nodep) override { iterateChildrenConst(nodep); }

public:
    explicit FinishTaskStateVisitor(AstNetlist* nodep) {
        iterateConst(nodep);
        propagateBlocked();
        propagateFinish();
    }
    bool supportsTask(const AstCFunc* nodep) const {
        const auto it = m_vertexps.find(nodep);
        return it != m_vertexps.end() && it->second->canExit() && !it->second->blocked();
    }
    bool taskMayFinish(const AstCFunc* nodep) const {
        const auto it = m_vertexps.find(nodep);
        return supportsTask(nodep) && it->second->hasFinish();
    }
};

class FinishVisitor final : public VNVisitor {
    // NODE STATE
    //  AstNodeProcedure/AstCFunc::user1p() -> AstJumpBlock*, exit for this source body
    //  AstFinish::user2()         -> bool, processed
    const VNUser1InUse m_user1InUse;
    const VNUser2InUse m_user2InUse;

    // STATE
    AstNode* m_procp = nullptr;  // Current supported source process or task
    const FinishTaskStateVisitor* const m_statep = nullptr;  // Qualified task call graph
    const bool m_finalLocal = false;  // Early, separately qualified final body
    VDouble0 m_statExits;  // Source-body exits added
    VDouble0 m_statCallExits;  // Post-call termination checks added

    AstJumpBlock* getExitBlock() {
        if (m_procp->user1p()) return VN_AS(m_procp->user1p(), JumpBlock);
        const AstCFunc* const funcp = VN_CAST(m_procp, CFunc);
        AstNode* const bodyp = funcp ? funcp->stmtsp() : VN_AS(m_procp, NodeProcedure)->stmtsp();
        UASSERT_OBJ(bodyp, m_procp, "Finish outside a source process body");
        VNRelinker relinker;
        bodyp->unlinkFrBackWithNext(&relinker);
        // A task may contain declarations after a finishing statement. Jump
        // out of their C++ scope rather than across their initialization.
        AstNode* const scopedBodyp = funcp ? new AstCLocalScope{funcp->fileline(), bodyp} : bodyp;
        AstJumpBlock* const blockp = new AstJumpBlock{m_procp->fileline(), scopedBodyp};
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
    void visit(AstCFunc* nodep) override {
        if (!m_statep || !m_statep->supportsTask(nodep)) return;
        VL_RESTORER(m_procp);
        m_procp = nodep;
        iterateAndNextNull(nodep->stmtsp());
    }
    // These boundaries have separate generated functions or return types.
    void visit(AstNodeFTask*) override {}
    void visit(AstFork*) override {}
    void visit(AstExprStmt*) override {}
    void visit(AstWith*) override {}
    void visit(AstStmtExpr* nodep) override {
        iterateChildren(nodep);
        if (!m_procp || !m_statep) return;
        const AstCCall* const callp = VN_CAST(nodep->exprp(), CCall);
        if (!callp || !m_statep->taskMayFinish(callp->funcp())) return;
        FileLine* const flp = nodep->fileline();
        // Worker threads can return before the queued finish callback sets
        // gotFinish. Check the existing pending-request flag as well.
        AstNodeExpr* const condp = new AstCExpr{flp,
                                                "VL_UNLIKELY(vlSymsp->_vm_contextp__->gotFinish()"
                                                " || vlSymsp->_vm_contextp__->finishPending())",
                                                1};
        nodep->addNextHere(new AstIf{flp, condp, new AstJumpGo{flp, getExitBlock()}});
        ++m_statCallExits;
    }
    void visit(AstFinish* nodep) override {
        if (!m_procp || nodep->user2SetOnce()) return;
        AstJumpBlock* const blockp = getExitBlock();
        nodep->addNextHere(new AstJumpGo{nodep->fileline(), blockp});
        ++m_statExits;
    }
    void visit(AstNode* nodep) override { iterateChildren(nodep); }

public:
    FinishVisitor(AstNetlist* nodep, const FinishTaskStateVisitor* statep)
        : m_statep{statep} {
        iterate(nodep);
    }
    explicit FinishVisitor(AstFinal* nodep)
        : m_procp{nodep}
        , m_finalLocal{true} {
        iterateAndNextNull(nodep->stmtsp());
    }
    ~FinishVisitor() override {
        V3Stats::addStat(m_finalLocal ? "Finish, final local exits" : "Finish, source body exits",
                         m_statExits);
        V3Stats::addStat("Finish, task call exits", m_statCallExits);
    }
};

// Inspect the original body before task inlining or expression lifting can
// erase a call boundary or introduce a local with a nontrivial lifetime.
class FinalLocalBodyVisitor final : public VNVisitorConst {
    bool m_blocked = false;
    bool m_hasFinish = false;

    void visit(AstFinish*) override { m_hasFinish = true; }
    void visit(AstNodeFTaskRef*) override { m_blocked = true; }
    void visit(AstNodeCCall*) override { m_blocked = true; }
    void visit(AstNodeFTask*) override { m_blocked = true; }
    void visit(AstCFunc*) override { m_blocked = true; }
    void visit(AstCExpr*) override { m_blocked = true; }
    void visit(AstCExprUser*) override { m_blocked = true; }
    void visit(AstCStmt*) override { m_blocked = true; }
    void visit(AstCStmtUser*) override { m_blocked = true; }
    void visit(AstCMethodHard*) override { m_blocked = true; }
    void visit(AstCAwait*) override { m_blocked = true; }
    void visit(AstCLocalScope*) override { m_blocked = true; }
    void visit(AstDelay*) override { m_blocked = true; }
    void visit(AstEventControl*) override { m_blocked = true; }
    void visit(AstWait*) override { m_blocked = true; }
    void visit(AstWaitFork*) override { m_blocked = true; }
    void visit(AstFork*) override { m_blocked = true; }
    void visit(AstExprStmt*) override { m_blocked = true; }
    void visit(AstWith*) override { m_blocked = true; }
    void visit(AstNewCopy*) override { m_blocked = true; }
    void visit(AstNewDynamic*) override { m_blocked = true; }
    void visit(AstUnlinkedRef*) override { m_blocked = true; }
    void visit(AstParseRef*) override { m_blocked = true; }
    void visit(AstMemberSel*) override { m_blocked = true; }
    void visit(AstSystemT*) override { m_blocked = true; }
    void visit(AstSystemF*) override { m_blocked = true; }
    void visit(AstVar*) override { m_blocked = true; }
    void visit(AstNodeVarRef* nodep) override {
        // Unresolved references can remain in dead code before elaboration.
        const AstVar* const varp = nodep->varp();
        const AstBasicDType* const dtypep
            = varp ? VN_CAST(varp->subDTypep(), BasicDType) : nullptr;
        if (!dtypep || !dtypep->isIntegralOrPacked()) m_blocked = true;
    }
    void visit(AstNode* nodep) override { iterateChildrenConst(nodep); }

public:
    explicit FinalLocalBodyVisitor(AstFinal* nodep) { iterateAndNextConstNull(nodep->stmtsp()); }
    bool eligible() const { return m_hasFinish && !m_blocked; }
};

class FinalLocalScopeVisitor final : public VNVisitorConst {
    const AstNodeModule* m_modp = nullptr;
    const AstNode* m_parentp = nullptr;
    const AstNodeModule* m_finalModp = nullptr;
    AstFinal* m_finalp = nullptr;
    bool m_finalDirect = false;
    unsigned m_topCount = 0;
    unsigned m_finalCount = 0;

    void visit(AstNodeModule* nodep) override {
        VL_RESTORER(m_modp);
        VL_RESTORER(m_parentp);
        m_modp = nodep;
        m_parentp = nodep;
        if (nodep->isTop() && !VN_IS(nodep, Package) && !VN_IS(nodep, Class)) ++m_topCount;
        iterateChildrenConst(nodep);
    }
    void visit(AstFinal* nodep) override {
        ++m_finalCount;
        m_finalp = nodep;
        m_finalModp = m_modp;
        m_finalDirect = m_parentp == m_modp;
    }
    void visit(AstNode* nodep) override {
        VL_RESTORER(m_parentp);
        m_parentp = nodep;
        iterateChildrenConst(nodep);
    }

public:
    explicit FinalLocalScopeVisitor(AstNetlist* nodep) { iterateConst(nodep); }
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

// Preserve source eligibility through parameterization, generate expansion and
// instance cloning. Scheduling will later connect these local final exits to
// one model-local termination flag; source calls must still be visible here.
class FinalEligibilityVisitor final : public VNVisitor {
    void visit(AstFinal* nodep) override {
        nodep->finishExitEligible(FinalLocalBodyVisitor{nodep}.eligible());
    }
    void visit(AstNode* nodep) override { iterateChildren(nodep); }

public:
    explicit FinalEligibilityVisitor(AstNetlist* nodep) { iterate(nodep); }
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
    { FinalEligibilityVisitor{nodep}; }
    if (const AstFinal* const finalp = FinalLocalScopeVisitor{nodep}.eligibleFinalp()) {
        FinalLocalRewriteVisitor{nodep, finalp};
    }
    V3Global::dumpCheckGlobalTree("finish-final-local", 0, dumpTreeEitherLevel() >= 3);
}

void V3Finish::finishAll(AstNetlist* nodep) {
    UINFO(2, __FUNCTION__ << ":");
    {
        const FinishTaskStateVisitor state{nodep};
        FinishVisitor{nodep, &state};
    }
    V3Global::dumpCheckGlobalTree("finish", 0, dumpTreeEitherLevel() >= 3);
}
