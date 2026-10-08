// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// DESCRIPTION: Verilator: Four-state logic handler
//
// Code available from: https://verilator.org
//
//*************************************************************************
//
// This program is free software; you can redistribute it and/or modify it
// under the terms of either the GNU Lesser General Public License Version 3
// or the Perl Artistic License Version 2.0.
// SPDX-FileCopyrightText: 2026 Wilson Snyder
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
//
//*************************************************************************
//
// - Evaluates logic types
//   `FourstateLogicTypePropagator` passes through a whole AST and marks logic types (uses user4
//   variable) for later use by `FourstateVisitor`.
//   This step is necessary since for now `V3With` treats two-state types and its four-state
//   counterparts almost interchangeably
//   The way `FourstateLogicTypePropagator` works is the same as standard expect.
//   E.g.:
//       (bit) = ((logic) & (bit))
//       ^~~~~    ^~~~~~~   ^~~~~
//       |        |         2-state expr
//       |        4-state expr
//       2-state expr
//
//       (logic) & (bit)
//       ^~~~~~~~~~~~~~~
//       4-state expr
//
//       So, it is turned into:
//       (bit) = bit'((logic) & logic'(bit))
//
//   But also, `FourstateLogicTypePropagator` tries to keep two-state logic wherever it is
//      possible - because it is faster. E.g.:
//        (bit) = ((bit) / (bit))
//        ^~~~~    ^~~~~   ^~~~~
//        |        |       2-state expr
//        |        2-state expr
//        2-state expr
//
//      ((bit) / (bit))
//      ^~~~~~~~~~~~~~~
//      4-state expr because dividing by 0 is a 'x
//
//      However, assuming that rhs is a const:
//        (bit) = ((bit) / (bit(7)))
//        ^~~~~    ^~~~~   ^~~~~
//        |        |       2-state expr
//        |        2-state expr
//        2-state expr
//
//      ((bit) / (bit(7)))
//      ^~~~~~~~~~~~~~~~~~
//      2-state expr because rhs for sure is non-zero known (non 'x/'z) value
//      and lhs is known as well
//
// - Splits four-state variables into two two-state variables which allows rest of Verilator
//   (almost) don't care about existence of four-state logic and handle only two-state logic. This
//   also implies that post V3Fourstate no new four-state variable/logic must not be created since
//   it won't be handled correctly anywhere.
//   E.g.:
//        logic a;
//        logic b;
//        logic c;
//        logic d;
//        d = a & (b | c);
//
//    Is turned into:
//        bit a;
//        bit a__Vxz;
//        bit b;
//        bit b__Vxz;
//        bit c;
//        bit c__Vxz;
//        bit d;
//        bit d__Vxz;
//        bit tmp0;
//        bit tmp1;
//        // Expression starts here
//        tmp0 = (((b__Vxz & c__Vxz) | (b__Vxz & ~c)) | (c__Vxz & ~b)); |> Lock of tmp0
//        tmp1 = ((b | c) | (b__Vxz | c__Vxz));                         |   |> Lock of tmp1
//        d = ((a | a__Vxz) & (tmp1 | tmp0));                           |   |
//        d__Vxz = (((a & tmp0) | (tmp1 & a__Vxz)) | (a__Vxz & tmp0));  |   |
//        // Whole expression ends here                                 Tmp variables are released
//
//     Note that every sub-expression gets its own temporary variable
//     unless it is trivial (e.g.: variable reference or const).
//     Worth noting is also the fact that temporary variables are released after the whole
//     expression end and they are reused later in different expressions - this reduce amount of
//     variables (this could be further optimized because right now variables are released at the
//     end of the whole expression and sometimes in complex expression some of them could be
//     released earlier - this is the same problem as with registers)
//
// - Handles wire conflicts
//   All AstAssignW are collected then if there is more than one assign to one variable a conflict
//   resolution is made.
//   Conflict resolution is made by creating a balanced binary tree and then applying associative
//   and commutative operation (different for normal conflict resolution different for triand and
//   different for trior) which resolves the conflict.
//
//   Currently there are two things to have in mind when it comes to conflict resolution:
//    - all assignments are merged under one `always` and if those assignments used an AstVarXRef
//      then it is unsupported case right now
//    - Mentioned conflict resolving operations are composed from basic bitwise operations and
//      currently they are not creating subexpression and temporaries therefore, their complexity
//      is O(m^log(n)) (where m is count of copies (~2-3) and n is amount of subexpressions (equal
//      to ~2*(count of assignments in conflict))). However, usually there are only a few
//      assignments in conflicts so, even though the complexity is bad it is still useable.
//
//*************************************************************************
// FourstateVisitor has a quite elaborate temporary variable system:
//  - createTmp() - creates new or return unused variable from a pool;
//                  variables lifetime lasts only for a current statement
//  - addPrecalculation() - adds a predeceasing statement (to current one) and extends temporary
//                          variables lifetime so they may be used in this statement
//                          - the same as addHereThisAsNext
//  - addNextCalculation() - adds successor statement - similar to addNextHere with key
//                           a difference that statements won't be in reversed order in case of
//                           multiple calls; additionally it extends lifetime of temporary
//                           variables
//
// To track all variables statements must create instance of StmtHelper at begining of a visitor
// and keep it till the end of it
//
//*************************************************************************
// TODOs:
//  - Rest of operators - not all operators are currently supported e.g.: powers
//  - Statements - cases etc.
//  - split assignW conflict resolution into multiple statements - see above
//  - four-states printing
//
//*************************************************************************

#include "V3PchAstNoMT.h"

#include "V3Fourstate.h"

#include "V3Stats.h"
#include "V3UniqueNames.h"
#include "V3Unknown.h"

#include <map>
#include <type_traits>
#include <utility>
#include <vector>

VL_DEFINE_DEBUG_FUNCTIONS;

#define FOURSTATE_VALUE_SUFFIX ""  // Needs to be empty so C++ api won't change
#define FOURSTATE_XZ_SUFFIX "__Vxz"  // Suffix added to four-state complement variables

namespace {
struct FourstatePair final {
    AstNodeExpr* valuep;
    AstNodeExpr* xzp;
};
enum LogicType : char {
    UNINITIALIZED = 0,  // Logic type has not been evaluated
    TWO_STATE,  // Two-state expression
    TWO_STATE_HARD,  // Expression is guaranteed by user that it won't be a four-state (propagator
                     // may not change it)
    TWO_STATE_WITH_FOUR_STATE_IN_SUBTREE,  // Two-state expression with four-state expression in
                                           // its subtree - this is necessary since some AstNodes
                                           // (e.g.: AstCastWrap or AstSel) may contain four-state
                                           // expression as a child but itself be a two-state. When
                                           // this occurs we need to know that for the sake of
                                           // short-circuiting (because we use precalculation
                                           // statements we need to know that we cannot put them
                                           // before current expression unconditionally)
    FOUR_STATE,  // Four-state expression
};
static void setLogicType(AstNodeExpr* const exprp, const LogicType logic) {
    exprp->user4(static_cast<int>(logic));
}
static LogicType getLogicType(const AstNodeExpr* const exprp) {
    return static_cast<LogicType>(exprp->user4());
}
static bool isTwostateHard(const AstNodeExpr* const exprp) {
    return getLogicType(exprp) == TWO_STATE_HARD;
}
static void setTwostate(AstNodeExpr* const exprp, bool hard = true) {
    setLogicType(exprp, hard ? TWO_STATE_HARD : TWO_STATE);
}
static void setFourstate(AstNodeExpr* const exprp, bool fourstate = true,
                         bool fourstateInSubTree = false) {
    if (isTwostateHard(exprp)) return;
    setLogicType(exprp, fourstate ? FOUR_STATE
                                  : (fourstateInSubTree ? TWO_STATE_WITH_FOUR_STATE_IN_SUBTREE
                                                        : TWO_STATE));
}
static bool isFourstate(const AstNodeExpr* const exprp) {
    const LogicType logic = getLogicType(exprp);
    UASSERT_OBJ(logic != UNINITIALIZED, exprp,
                "Logic type of expression: " << exprp->typeName() << " is unevaluated");
    return logic == FOUR_STATE;
}
// Return true when the expression is two-state and has four-state expression in sub-tree
static bool hasFourstateInSubtree(const AstNodeExpr* const exprp) {
    return getLogicType(exprp) == TWO_STATE_WITH_FOUR_STATE_IN_SUBTREE;
}

// Trait checking whether instance of type T can be used as an reducer, for assign conflict
// resolution
template <typename T, typename = void>
struct ReducerTrait final : std::false_type {};
template <typename T>
struct ReducerTrait<
    T, std::enable_if_t<std::is_same<decltype(std::declval<T>()(std::declval<FourstatePair>(),
                                                                std::declval<FourstatePair>())),
                                     FourstatePair>::value>>
    final : std::true_type {};

static bool isStaticlyNGte(const V3Number& msb, const AstNodeExpr* const exprp) {
    FileLine* const flp = exprp->fileline();
    if (const AstConst* const constp = VN_CAST(exprp, Const)) {
        return constp->num().isAnyXZ() || V3Number{flp, 1, 0}.opLt(msb, constp->num()).isNeqZero();
    }
    return false;
}
static bool needsSplitting(const AstNodeDType* const dtypep) {
    const AstNodeDType* const skipDTypep = dtypep->skipRefp();
    if (const AstBasicDType* const basicp = VN_CAST(skipDTypep, BasicDType)) {
        return basicp->isFourstate();
    }
    if (const AstStructDType* const structDtypep = VN_CAST(skipDTypep, StructDType)) {
        return structDtypep->isFourstate();
    }
    if (const AstPackArrayDType* const containerDTypep = VN_CAST(skipDTypep, PackArrayDType)) {
        return needsSplitting(containerDTypep->subDTypep()->skipRefp());
    }
    if (const AstUnpackArrayDType* const containerDTypep = VN_CAST(skipDTypep, UnpackArrayDType)) {
        return needsSplitting(containerDTypep->subDTypep()->skipRefp());
    }
    if (const AstDynArrayDType* const containerDTypep = VN_CAST(dtypep, DynArrayDType)) {
        return needsSplitting(containerDTypep->subDTypep()->skipRefp());
    }
    return false;
}

class FTaskPortsHelper final {
    std::vector<AstVar*>
        m_currentFTaskRefPortps;  // Ports of FTask in order so we can connect AstArgs to them
    std::map<std::string, AstVar*>
        m_currentFTaskRefPortpsNamesToVarps;  // Ports names to their Vars so we can handle
                                              // named arguments

public:
    explicit FTaskPortsHelper(const AstNodeFTask* const ftaskp) {
        // TODO: Add caching
        UASSERT_OBJ(m_currentFTaskRefPortps.empty(), ftaskp,
                    "Tried to build a port map while another exists");
        UASSERT_OBJ(m_currentFTaskRefPortpsNamesToVarps.empty(), ftaskp,
                    "Tried to build a port map while another exists");
        for (AstNode* stmtp = ftaskp->stmtsp(); stmtp; stmtp = stmtp->nextp()) {
            if (AstVar* const varp = VN_CAST(stmtp, Var)) {
                if (varp->direction().isAny()
                    && !(varp->fourstateComplementp() || varp->isFourstateComplement())) {
                    m_currentFTaskRefPortps.push_back(varp);
                    m_currentFTaskRefPortpsNamesToVarps[varp->name()] = varp;
                }
            }
        }
    }

    AstVar* getArgPortVar(const std::string& name, const size_t idx) const {
        return name.empty() ? m_currentFTaskRefPortps.at(idx)
                            : m_currentFTaskRefPortpsNamesToVarps.at(name);
    }
    AstVar* lastp() const {
        return m_currentFTaskRefPortps.empty() ? nullptr : m_currentFTaskRefPortps.back();
    }
};
}  // namespace

// Propagates the logic type (two or four-state) on AstNodeExpr
// Needed as V3Width not always gives a correct logic type
class FourstateLogicTypePropagator final : public VNVisitor {
    bool m_fourstateInSubtree
        = false;  // Whether a four-state expression is present in a sub-tree of an expression

    void iterateChildrenSeparately(AstNode* const nodep) {
        auto foreach = [this](AstNode* nodep) {
            bool fourstateInSubtree = false;
            for (; nodep; nodep = nodep->nextp()) {
                m_fourstateInSubtree = false;
                iterate(nodep);
                fourstateInSubtree |= m_fourstateInSubtree;
            }
            return fourstateInSubtree;
        };
        // Cast to char so, there is no warnings
        m_fourstateInSubtree = static_cast<bool>(static_cast<char>(foreach(nodep->op1p()))
                                                 | static_cast<char>(foreach(nodep->op2p()))
                                                 | static_cast<char>(foreach(nodep->op3p()))
                                                 | static_cast<char>(foreach(nodep->op4p())));
    }

    // VISITORS
    void visit(AstConst* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, nodep->num().isAnyXZ(), m_fourstateInSubtree);
        m_fourstateInSubtree |= isFourstate(nodep);
    }
    void visit(AstNodeVarRef* const nodep) override {
        setFourstate(nodep, needsSplitting(nodep->varp()->dtypep()), m_fourstateInSubtree);
        m_fourstateInSubtree |= isFourstate(nodep);
    }
    void visit(AstNodeFTaskRef* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep,
                     nodep->taskp()->fvarp() && needsSplitting(nodep->taskp()->fvarp()->dtypep()),
                     m_fourstateInSubtree);
        m_fourstateInSubtree |= isFourstate(nodep);
    }
    void visit(AstNodeUniop* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->lhsp()), m_fourstateInSubtree);
    }
    void visit(AstCastWrap* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, needsSplitting(nodep->dtypep()), m_fourstateInSubtree);
        m_fourstateInSubtree |= isFourstate(nodep);
    }
    void visit(AstNodeBiop* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->lhsp()) || isFourstate(nodep->rhsp()),
                     m_fourstateInSubtree);
    }
    void visit(AstEqCase* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstNeqCase* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstDiv* nodep) override {
        iterateChildrenSeparately(nodep);
        if (AstConst* const constp = VN_CAST(nodep->rhsp(), Const)) {
            setFourstate(nodep,
                         isFourstate(nodep->lhsp()) || constp->num().isEqZero()
                             || constp->num().isAnyXZ(),
                         m_fourstateInSubtree);
        } else {
            setFourstate(nodep, true, m_fourstateInSubtree);
        }
        m_fourstateInSubtree |= isFourstate(nodep);
    }
    void visit(AstNodeTriop* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep,
                     isFourstate(nodep->lhsp()) || isFourstate(nodep->rhsp())
                         || isFourstate(nodep->thsp()),
                     m_fourstateInSubtree);
    }
    void visit(AstCond* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(
            nodep,
            isFourstate(nodep->thenp()) || isFourstate(nodep->elsep())
                || (isFourstate(nodep->condp()) && nodep->thenp()->dtypep()->isIntegralOrPacked()),
            m_fourstateInSubtree);
    }
    void visit(AstCReset* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    void visit(AstCountBits* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    void visit(AstCountOnes* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    void visit(AstSFormatArg* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->exprp()), m_fourstateInSubtree);
    }
    void visit(AstSel* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->fromp()), m_fourstateInSubtree);
    }

    void visit(AstArraySel* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, needsSplitting(nodep->fromp()->dtypep()), m_fourstateInSubtree);
    }

    void visit(AstSliceSel* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, needsSplitting(nodep->fromp()->dtypep()), m_fourstateInSubtree);
    }

    void visit(AstCExprUser* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstRedOr* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->lhsp()), m_fourstateInSubtree);
    }
    void visit(AstTime* const nodep) override {
        iterateChildrenSeparately(nodep);
        // Time is actually a fourstate but we never put `x` or `z` there
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstIToRD* const nodep) override {
        iterateChildrenSeparately(nodep);
        // Real values have no X/Z bits. Integer conversion clears unknown bits.
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstISToRD* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstRToIRoundS* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstRToIS* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstScopeName* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstClassOrPackageRef* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    void visit(AstCMethodHard* const nodep) override {
        iterateChildrenSeparately(nodep);
        switch (nodep->method()) {
        case VCMethod::ARRAY_AT:
        case VCMethod::ARRAY_AT_WRITE:
        case VCMethod::DYN_CLEAR:
        case VCMethod::DYN_RENEW:
        case VCMethod::DYN_RENEW_COPY:
        case VCMethod::DYN_SIZE: break;
        default:
            if (needsSplitting(nodep->fromp()->dtypep())) {
                nodep->v3warn(E_UNSUPPORTED,
                              "Unsupported CMethod hard: " << nodep->method().ascii());
            }
            break;
        }
        setFourstate(nodep, needsSplitting(nodep->fromp()->dtypep()), m_fourstateInSubtree);
    }

    void visit(AstCExpr* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstRand* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstMemberSel* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, needsSplitting(nodep->varp()->dtypep()), m_fourstateInSubtree);
    }
    void visit(AstSFormatF* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    // void visit(AstStructSel* const nodep) override {
    //     iterateChildrenSeparately(nodep);
    //     setFourstate(nodep, isFourstate(nodep->fromp()), m_fourstateInSubtree);
    // }

    void visit(AstExprStmt* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->resultp()), m_fourstateInSubtree);
    }

    void visit(AstConsPackMember* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->rhsp()), m_fourstateInSubtree);
    }

    void visit(AstStructSel* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, isFourstate(nodep->fromp()), m_fourstateInSubtree);
    }
    void visit(AstFOpen* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstSScanF* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstFourstateExpr* const nodep) override {
        iterateChildrenSeparately(nodep);
        // The `false` is a lie but this visitor is here just for debug purposes so, after
        // FourstateVisitor we can check whether any four-state expression has not been handled.
        // This lie is safe since before V3Fourstate no AstFourstateExpr exists
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    void visit(AstInsideRange* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstReadMemFile* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }
    void visit(AstReadMemPair* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    void visit(AstSampled* const nodep) override {
        iterateChildrenSeparately(nodep);
        if (const AstNodeExpr* const exprp = VN_CAST(nodep->exprp(), NodeExpr)) {
            setFourstate(nodep, isFourstate(exprp), m_fourstateInSubtree);
        } else {
            setFourstate(nodep, false, m_fourstateInSubtree);
            nodep->v3fatalSrc("$sampled with non-expressions argument in four-state mode is "
                              "unsupported");  // probably unreachable
        }
    }

    void visit(AstIsUnknown* const nodep) override {
        iterateChildrenSeparately(nodep);
        setFourstate(nodep, false, m_fourstateInSubtree);
    }

    void visit(AstNodeExpr* const nodep) override {
        iterateChildrenSeparately(nodep);
        UASSERT_OBJ(nodep->dtypep(), nodep, "Expression has no dtype");
        if (AstBasicDType* const basicp = VN_CAST(nodep->dtypep()->skipRefOrNullp(), BasicDType)) {
            if (basicp->keyword().isIntNumeric()) {
                nodep->v3warn(E_UNSUPPORTED, "Unsupported: Operator: " << nodep->typeName()
                                                                       << " with --fourstate");
            }
        }
        setFourstate(nodep, false, m_fourstateInSubtree);  // Set an arbitrary logic type
    }
    void visit(AstNode* nodep) override {
        VL_RESTORER(m_fourstateInSubtree);
        iterateChildrenSeparately(nodep);
    }

public:
    explicit FourstateLogicTypePropagator(AstNode* const nodep) { iterate(nodep); }
    ~FourstateLogicTypePropagator() override = default;
};

// Audit unsplit implicit-pull nets before any write is transformed. Applying a pull to an
// individual contribution is only correct for a single whole, untimed continuous driver.
class FourstatePullVisitor final : public VNVisitorConst {
    struct DriverInfo final {
        AstNodeModule* modulep = nullptr;
        AstNodeModule* assignModulep = nullptr;
        AstAssignW* assignp = nullptr;
        unsigned writes = 0;
        bool knownInitializer = false;
        string reason;
    };
    std::map<AstVar*, DriverInfo> m_drivers;
    std::vector<AstVar*> m_vars;
    AstNodeModule* m_modp = nullptr;
    AstAssignW* m_assignp = nullptr;
    AstNodeAssign* m_nodeAssignp = nullptr;
    string m_context;
    bool m_alias = false;
    bool m_initial = false;

    static bool isPullNet(const AstVar* const varp) {
        return varp->isPullup() || varp->isPulldown();
    }
    static void reject(DriverInfo& info, const string& reason) {
        if (info.reason.empty()) info.reason = reason;
    }
    void visit(AstNodeModule* nodep) override {
        VL_RESTORER(m_modp);
        m_modp = nodep;
        iterateChildrenConst(nodep);
    }
    void visit(AstVar* nodep) override {
        if (isPullNet(nodep)) {
            DriverInfo& info = m_drivers[nodep];
            info.modulep = m_modp;
            m_vars.push_back(nodep);
            if (!nodep->isNet() || nodep->isIO() || nodep->isClassMember() || nodep->isFuncLocal()
                || nodep->lifetime().isAutomatic()
                || !nodep->dtypep()->skipRefp()->isIntegralOrPacked()) {
                reject(info, "nonlocal or nonpacked variable");
            } else if (nodep->isForced() || nodep->isSigUserRWPublic()) {
                reject(info, "force or external write access");
            } else if (nodep->delayp()) {
                reject(info, "net delay");
            } else if (nodep->hasStrengthAssignment()) {
                reject(info, "explicit drive strength");
            }
        }
        iterateChildrenConst(nodep);
    }
    void visit(AstNodeAssign* nodep) override {
        VL_RESTORER(m_assignp);
        VL_RESTORER(m_nodeAssignp);
        m_assignp = VN_CAST(nodep, AssignW);
        m_nodeAssignp = nodep;
        iterateChildrenConst(nodep);
    }
    void visit(AstInitial* nodep) override {
        VL_RESTORER(m_initial);
        m_initial = true;
        iterateChildrenConst(nodep);
    }
    void visit(AstNodeVarRef* nodep) override {
        AstVar* const varp = nodep->varp();
        if (!isPullNet(varp)) return;
        DriverInfo& info = m_drivers[varp];
        if (m_alias) {
            ++info.writes;
            reject(info, m_context);
            return;
        }
        if (!nodep->access().isWriteOrRW()) return;
        ++info.writes;
        if (!m_context.empty()) {
            reject(info, m_context);
            return;
        } else if (VN_IS(nodep, VarXRef)) {
            reject(info, "hierarchical writer");
        } else if (!m_assignp && m_initial && VN_IS(m_nodeAssignp, Assign)
                   && m_nodeAssignp->lhsp() == nodep && !m_nodeAssignp->timingControlp()
                   && varp->isConst()) {
            // V3Const can turn a known constant continuous driver into an initial assignment.
            // Preserve that optimized form, without admitting general procedural net writes.
            const AstConst* const constp = VN_CAST(varp->valuep(), Const);
            if (constp && !constp->num().isFourState()
                && constp->sameTree(m_nodeAssignp->rhsp())) {
                info.knownInitializer = true;
                info.assignModulep = m_modp;
            } else {
                reject(info, "write outside a whole continuous assignment");
            }
        } else if (!m_assignp || m_assignp->lhsp() != nodep) {
            reject(info, "write outside a whole continuous assignment");
        } else if (m_assignp->timingControlp()) {
            reject(info, "assignment delay");
        } else if (m_assignp->strengthSpecp()) {
            reject(info, "explicit drive strength");
        } else {
            info.assignp = m_assignp;
            info.assignModulep = m_modp;
        }
    }
    void visit(AstPin* nodep) override {
        VL_RESTORER_COPY(m_context);
        if (AstVar* const varp = nodep->modVarp()) {
            if (isPullNet(varp) && varp->direction().isNonOutput()) {
                DriverInfo& info = m_drivers[varp];
                ++info.writes;
                reject(info, "port or pin writer");
            }
            // Input actuals are reads. Only output/inout/ref actuals contribute a driver.
            if (varp->isWritable()) m_context = "port or pin writer";
        }
        iterateChildrenConst(nodep);
    }
    void visit(AstAlias* nodep) override {
        VL_RESTORER_COPY(m_context);
        VL_RESTORER(m_alias);
        m_context = "alias";
        m_alias = true;
        iterateChildrenConst(nodep);
    }
    void visit(AstAliasScope* nodep) override {
        VL_RESTORER_COPY(m_context);
        VL_RESTORER(m_alias);
        m_context = "alias";
        m_alias = true;
        iterateChildrenConst(nodep);
    }
    void visit(AstRelease* nodep) override {
        VL_RESTORER_COPY(m_context);
        m_context = "force or release";
        iterateChildrenConst(nodep);
    }
    void visit(AstAssignForce* nodep) override {
        VL_RESTORER_COPY(m_context);
        m_context = "force or release";
        iterateChildrenConst(nodep);
    }
    void visit(AstPull* nodep) override {
        VL_RESTORER_COPY(m_context);
        m_context = "explicit pull primitive";
        iterateChildrenConst(nodep);
    }
    void visit(AstNode* nodep) override { iterateChildrenConst(nodep); }

public:
    static std::map<const AstNodeAssign*, bool> collect(AstNetlist* const netlistp) {
        FourstatePullVisitor visitor;
        visitor.iterateConst(netlistp);
        std::map<const AstNodeAssign*, bool> assignments;
        for (AstVar* const varp : visitor.m_vars) {
            DriverInfo& info = visitor.m_drivers.at(varp);
            if (!info.writes) continue;  // Preserve the existing undriven pull path.
            if (info.writes == 1 && info.knownInitializer && info.reason.empty()
                && info.assignModulep == info.modulep
                && varp->dtypep()->skipRefp()->isIntegralOrPacked() && !varp->isForced()
                && !varp->isSigUserRWPublic() && !varp->delayp()
                && !varp->hasStrengthAssignment()) {
                continue;  // No Z bits can require a fallback in a known constant driver.
            }
            if (info.writes != 1) reject(info, "multiple drivers");
            if (info.assignp && info.assignModulep != info.modulep) {
                reject(info, "nonlocal writer");
            }
            if (info.reason.empty()) {
                UASSERT_OBJ(info.assignp, varp, "Pull driver audit lost assignment");
                assignments.emplace(info.assignp, varp->isPullup());
            } else {
                varp->v3warn(E_UNSUPPORTED, "Unsupported: Driven tri0/tri1 net "
                                                << varp->prettyNameQ()
                                                << " with --fourstate: " << info.reason << ".");
            }
        }
        return assignments;
    }
};

// Splits AstVar of four-state type into two two-states
// Transforms four-state logic expressions into two-states
// Handles AssignW conflict resolution
class FourstateVisitor final : public VNVisitor {
    const VNUser1InUse m_user1InUse;
    const VNUser2InUse m_user2InUse;
    const VNUser3InUse m_user3InUse;
    const VNUser4InUse m_user4InUse;
    // Node status
    // AstVar::user1p           ->  AstVar*.        Where is value part of splitted variable - xz
    // AstNodeExpr::user1p      ->  AstNodeExpr*.   Expression evaluating value component
    // AstNodeExpr::user2p      ->  AstNodeExpr*.   Expression evaluating xz component
    // AstSel::user3            ->  bool.           Was processed
    // AstNodeFTaskRef::user3   ->  bool.           Was processed
    // AstNodeExpr::user4       ->  LogicType.      Expression logic type (whether it is four
    //                                              or two state)

    static void setValuePartVarp(AstVar* const varp, AstVar* const valuep) {
        varp->user1p(valuep);
    }
    static AstVar* getValuePartVarp(AstVar* const varp) { return VN_AS(varp->user1p(), Var); }
    static void setSelpHandled(AstNodeExpr* const selp) { selp->user3(1); }
    static bool isSelpHandled(AstNodeExpr* const selp) { return selp->user3(); }
    static void setFTaskRefHandled(AstNodeFTaskRef* const ftaskRefp) { ftaskRefp->user3(1); }
    static bool isFTaskRefHandled(AstNodeFTaskRef* const ftaskRefp) { return ftaskRefp->user3(); }
    static void setExprValuep(AstNodeExpr* const fourstateExprp, AstNode* const valuep) {
        fourstateExprp->user1p(valuep);
    }
    static AstNodeExpr* getExprValuep(const AstNodeExpr* const fourstateExprp) {
        return VN_AS(fourstateExprp->user1p(), NodeExpr);
    }
    static void setExprXZp(AstNodeExpr* const fourstateExprp, AstNode* const xzp) {
        fourstateExprp->user2p(xzp);
    }
    static AstNodeExpr* getExprXZp(const AstNodeExpr* const fourstateExprp) {
        return VN_AS(fourstateExprp->user2p(), NodeExpr);
    }
    static void castFourstateWarn(const AstNodeExpr* const exprp) {
        exprp->v3warn(CASTFOURSTATE, "Unsupported: Implicitly casting to two-state logic\n"
                                         << exprp->fileline()->warnMore()
                                         << "... Suggest cast to two-state logic explicitly");
    }

    V3UniqueNames m_tmpNames;  // Unique names generator for temporary variables
    V3UniqueNames m_pinHelpersNames;

    AstNode* m_currentTmpSpotp = nullptr;  // Node after which put AstVar* for temporary variable
    bool m_tmpFuncLocal
        = false;  // Whether temporary variables shall be created as function locals
    AstNode* m_currentStmtp = nullptr;  // Current statement or declarative coverage anchor
    AstNode* m_lastCalculationStatp = nullptr;  // Last calculation statement
    AstNodeModule* m_modp = nullptr;  // Current module
    std::vector<AstVar*> m_varpsToRemove;  // Vars to unlink and remove in destructor
    AstNodeExpr* m_caseMaskp = nullptr;
    VCaseType m_caseType = VCaseType::CT_CASE;  // Active case wildcard semantics

    std::vector<FTaskPortsHelper> m_ftaskPortHelpers;  // Cache of FTaskPortsHelpers

    // array - whether numeric
    // map - width
    std::array<std::map<int, std::vector<AstVar*>>, 2>
        m_tmpUnusedVarps;  // Existing not in use temporary variables
    std::vector<AstVar*> m_tmpVarpsInUse;  // Temporary variables that are being currently used
    std::vector<std::pair<const AstNode*, size_t>>
        m_tmpVarReleaserStack;  // Stack used by TmpVarsReleaser to keep track of ownership and
                                // count of vars to release

    struct ArrayIndexCapture final {
        AstVar* const valuep;
        AstVar* const badp;
    };
    std::map<const AstArraySel*, ArrayIndexCapture>
        m_arrayIndexCaptures;  // Index snapshots shared by the value and X/Z selections
    std::map<const AstNodeAssign*, bool>
        m_pullAssignments;  // Audited whole continuous assignment -> implicit pull value
    uint32_t m_statPullFallbacks = 0;  // Whole continuous implicit-pull drivers lowered

    // Original AstVar* and pair of assignments <value, xz>
    using NetToAssignWps
        = std::map<const AstVar*, std::vector<std::pair<AstAssignW*, AstAssignW*>>>;
    NetToAssignWps m_assignWToTrior;  // Map from variables to their AssignWs
    NetToAssignWps m_assignWToTriand;  // Map from variables to their AssignWs
    NetToAssignWps m_assignWToWire;  // Map from variables to their AssignWs

    static FourstatePair triReducer(const FourstatePair& a, const FourstatePair& b) {
        FileLine* const flp = a.valuep->fileline();
        FourstatePair result;
        {
            // a.value | b.value
            result.valuep = new AstOr{flp, a.valuep, b.valuep};
        }
        {
            // (a.value & a.xz) | (b.value & b.xz) | (a.xz & b.xz) | (a.value & ~b.value & ~b.xz) |
            // (b.value & ~a.value & ~a.xz)
            result.xzp = new AstOr{
                flp,
                new AstOr{flp,
                          new AstOr{flp, new AstAnd{flp, a.valuep->cloneTree(false), a.xzp},
                                    new AstAnd{flp, b.valuep->cloneTree(false), b.xzp}},
                          new AstAnd{flp, a.xzp->cloneTree(false), b.xzp->cloneTree(false)}},
                new AstOr{flp,
                          new AstAnd{flp,
                                     new AstAnd{flp, a.valuep->cloneTree(false),
                                                new AstNot{flp, b.valuep->cloneTree(false)}},
                                     new AstNot{flp, b.xzp->cloneTree(false)}},
                          new AstAnd{flp,
                                     new AstAnd{flp, b.valuep->cloneTree(false),
                                                new AstNot{flp, a.valuep->cloneTree(false)}},
                                     new AstNot{flp, a.xzp->cloneTree(false)}}}};
        }
        return result;
    }
    static FourstatePair triandReducer(const FourstatePair& a, const FourstatePair& b) {
        FileLine* const flp = a.valuep->fileline();
        FourstatePair result;
        {
            // (a.value & b.xz) | (b.value & a.xz) | (a.value & b.value)
            result.valuep = new AstOr{
                flp,
                new AstOr{flp, new AstAnd{flp, a.valuep, b.xzp}, new AstAnd{flp, b.valuep, a.xzp}},
                new AstAnd{flp, a.valuep->cloneTree(false), b.valuep->cloneTree(false)}};
        }
        {
            // (a.xz & b.xz) | (a.value & b.value & a.xz) | (a.value & b.value & b.xz)
            result.xzp = new AstOr{
                flp,
                new AstOr{flp, new AstAnd{flp, a.xzp->cloneTree(false), b.xzp->cloneTree(false)},
                          new AstAnd{flp,
                                     new AstAnd{flp, a.valuep->cloneTree(false),
                                                b.valuep->cloneTree(false)},
                                     b.xzp->cloneTree(false)}},
                new AstAnd{flp,
                           new AstAnd{flp, a.valuep->cloneTree(false), b.valuep->cloneTree(false)},
                           b.xzp->cloneTree(false)}};
        }
        return result;
    }
    static FourstatePair triorReducer(const FourstatePair& a, const FourstatePair& b) {
        FileLine* const flp = a.valuep->fileline();
        FourstatePair result;
        {
            // a.value | b.value
            result.valuep = new AstOr{flp, a.valuep, b.valuep};
        }
        {
            // (a.value | b.xz) & (b.value | a.xz) & (a.xz | ~a.value) & (b.xz | ~b.value)
            result.xzp
                = new AstAnd{flp,
                             new AstAnd{flp, new AstOr{flp, a.valuep->cloneTree(false), b.xzp},
                                        new AstOr{flp, b.valuep->cloneTree(false), a.xzp}},
                             new AstAnd{flp,
                                        new AstOr{flp, a.xzp->cloneTree(false),
                                                  new AstNot{flp, a.valuep->cloneTree(false)}},
                                        new AstOr{flp, b.xzp->cloneTree(false),
                                                  new AstNot{flp, b.valuep->cloneTree(false)}}}};
        }
        return result;
    }

    template <typename Reducer_T>
    static FourstatePair buildTree(std::vector<FourstatePair> exprps, Reducer_T&& reducer) {
        static_assert(ReducerTrait<Reducer_T>::value, "Reducer_T shall fullfill reducer trait");
        while (exprps.size() > 1) {
            const size_t halfSize = exprps.size() / 2;
            for (size_t i = 0; i < halfSize; ++i) {
                exprps[i] = reducer(exprps[i], exprps.back());
                exprps.pop_back();
            }
        }
        return exprps[0];
    }
    template <typename Reducer_T>
    static void triorTriandReduce(const NetToAssignWps& assignWs, Reducer_T&& reducer) {
        for (const auto& pair : assignWs) {
            const auto& assignps = pair.second;
            if (assignps.size() < 2) continue;
            std::vector<FourstatePair> exprps;
            exprps.reserve(assignps.size());
            for (const auto& assignp : assignps) {
                exprps.push_back({assignp.first->rhsp()->unlinkFrBack(),
                                  assignp.second->rhsp()->unlinkFrBack()});
                const AstVarXRef* xRefp = nullptr;
                if (exprps.back().valuep->exists([&xRefp](const AstVarXRef* const refp) {
                        xRefp = refp;
                        return true;
                    })) {
                    // The issue is when hierarchical reference is being moved to another module.
                    // Then it shall be fixed
                    xRefp->v3warn(E_UNSUPPORTED,
                                  "Unsupported: Hierarchical references with --fourstate");
                }
            }
            FourstatePair result = buildTree(std::move(exprps), reducer);
            assignps[0].first->rhsp(result.valuep);
            assignps[0].second->rhsp(result.xzp);
            for (size_t i = 1; i < assignps.size(); ++i) {
                assignps[i].first->unlinkFrBack()->deleteTree();
                assignps[i].second->unlinkFrBack()->deleteTree();
            }
        }
    }

    static AstConst* createZeroOrOnesp(const AstNodeExpr* const exprp, const bool ones = false) {
        AstConst* const resultp
            = new AstConst{exprp->fileline(), AstConst::WidthedValue{}, exprp->width(), 0};
        resultp->dtypeSetBitUnsized(exprp->width(), exprp->widthMin(), exprp->dtypep()->numeric());
        if (ones) resultp->num().setAllBits1();
        setFourstate(resultp, false);
        return resultp;
    }

    // {whether supported, whether four state} - second is needed for the recursion
    static std::pair<bool, bool> isDTypepSupported(const AstNodeDType* const dtypep) {
        if (const AstBasicDType* const basicp = VN_CAST(dtypep, BasicDType)) {
            return {true, basicp->isFourstate()};
        }
        if (const AstStructDType* const structDtypep = VN_CAST(dtypep, StructDType)) {
            return {true, structDtypep->isFourstate()};
        }
        if (const AstNodeUOrStructDType* const containerDTypep
            = VN_CAST(dtypep, NodeUOrStructDType)) {
            return {!containerDTypep->isFourstate(), containerDTypep->isFourstate()};
        }
        if (const AstSampleQueueDType* const containerDTypep = VN_CAST(dtypep, SampleQueueDType)) {
            std::pair<bool, bool> subDtype
                = isDTypepSupported(containerDTypep->subDTypep()->skipRefp());
            return {subDtype.first && !subDtype.second, false};
        }
        if (const AstQueueDType* const containerDTypep = VN_CAST(dtypep, QueueDType)) {
            std::pair<bool, bool> subDtype
                = isDTypepSupported(containerDTypep->subDTypep()->skipRefp());
            return {subDtype.first && !subDtype.second, false};
        }
        if (const AstAssocArrayDType* const containerDTypep = VN_CAST(dtypep, AssocArrayDType)) {
            std::pair<bool, bool> subDtype
                = isDTypepSupported(containerDTypep->subDTypep()->skipRefp());
            return {subDtype.first && !subDtype.second, false};
        }
        // if (const AstUnpackArrayDType* const containerDTypep = VN_CAST(dtypep,
        // UnpackArrayDType)) {
        //     std::pair<bool, bool> subDtype
        //         = isDTypepSupported(containerDTypep->subDTypep()->skipRefp());
        //     return {subDtype.first && !subDtype.second, false};
        // }
        if (const AstPackArrayDType* const containerDTypep = VN_CAST(dtypep, PackArrayDType)) {
            std::pair<bool, bool> subDtype
                = isDTypepSupported(containerDTypep->subDTypep()->skipRefp());
            return subDtype;
        }
        return {true, false};
    }

    void assignWConflictResolution(AstVar* const varp, AstAssignW* const assignwValuep,
                                   AstAssignW* const assignwXzp) {
        // Assignments to different things are unsupported
        switch (varp->varType()) {
        case VVarType::TRIOR:
            m_assignWToTrior[varp].emplace_back(assignwValuep, assignwXzp);
            break;
        case VVarType::TRIAND:
            m_assignWToTriand[varp].emplace_back(assignwValuep, assignwXzp);
            break;
        case VVarType::VAR:
        case VVarType::TRIWIRE:
        case VVarType::PORT:  // The issue with ports is that we lose information about the wire
                              // type (tri/triand/trior)
        case VVarType::WIRE: m_assignWToWire[varp].emplace_back(assignwValuep, assignwXzp); break;
        case VVarType::SUPPLY0:
        case VVarType::SUPPLY1:
        case VVarType::TRI0:
        case VVarType::TRI1:
            varp->v3warn(E_UNSUPPORTED,
                         "Unsupported: supply0/tri0 and supply1/tri1 with --fourstate");
            break;
        default:  // LCOV_EXCL_LINE
            assignwValuep->v3fatalSrc(
                "Unexpected variable type on lhs of assign: " << varp->varType().ascii());
            break;
        }
    }

    struct TmpVarsReleaser final {
        FourstateVisitor& m_visitor;  // Visitor
        const AstNode* const m_owner;  // Releasing owner
        explicit TmpVarsReleaser(FourstateVisitor& visitor, const AstNode* const owner)
            : m_visitor{visitor}
            , m_owner{owner} {
            if (m_visitor.m_tmpVarReleaserStack.empty()
                || m_visitor.m_tmpVarReleaserStack.back().first != m_owner) {
                m_visitor.m_tmpVarReleaserStack.emplace_back(m_owner,
                                                             m_visitor.m_tmpVarpsInUse.size());
            }
        }
        ~TmpVarsReleaser() {
            UASSERT_OBJ(!m_visitor.m_tmpVarReleaserStack.empty(), m_owner,
                        "m_tmpVarReleaserStack should never be empty if TmpVarsReleaser exists");
            if (m_visitor.m_tmpVarReleaserStack.back().first == m_owner) {
                const size_t targetSize = m_visitor.m_tmpVarReleaserStack.back().second;
                m_visitor.m_tmpVarReleaserStack.pop_back();
                UASSERT_OBJ(targetSize <= m_visitor.m_tmpVarpsInUse.size(), m_owner,
                            "There is less used tmp variables than before");
                for (size_t i = targetSize; i < m_visitor.m_tmpVarpsInUse.size(); ++i) {
                    AstVar* const varp = m_visitor.m_tmpVarpsInUse[i];
                    m_visitor
                        .m_tmpUnusedVarps[varp->dtypep()->numeric().isSigned() ? 1 : 0]
                                         [varp->width()]
                        .push_back(varp);
                }
                m_visitor.m_tmpVarpsInUse.resize(targetSize);
            }
            UASSERT_OBJ(m_visitor.m_tmpVarReleaserStack.empty()
                            || m_visitor.m_tmpVarReleaserStack.back().first != m_owner,
                        m_owner,
                        "There should not be two consecutive stack frames with the same owner");
        }
    };
    class StmtHelper final {
        const VRestorerTrivial<AstNode*> m_currentStmtRestorer;
        const VRestorerTrivial<AstNode*> m_lastStmtRestorer;
        const VRestorerClear<decltype(m_arrayIndexCaptures)> m_arrayIndexRestorer;
        const TmpVarsReleaser m_tmpVarsReleaser;

    public:
        StmtHelper(FourstateVisitor& visitor, AstNode* const stmtp)
            : m_currentStmtRestorer{visitor.m_currentStmtp}
            , m_lastStmtRestorer{visitor.m_lastCalculationStatp}
            , m_arrayIndexRestorer{visitor.m_arrayIndexCaptures}
            , m_tmpVarsReleaser{visitor, stmtp} {
            visitor.m_lastCalculationStatp = visitor.m_currentStmtp = stmtp;
        }
    };
    class StatementPlaceHolder final {
        AstNodeStmt* const m_stmtp;
        const StmtHelper m_stmtHelper;

    public:
        StatementPlaceHolder(FourstateVisitor& visitor, FileLine* const flp)
            : m_stmtp{new AstBegin{flp, "", nullptr, true}}
            , m_stmtHelper{visitor, m_stmtp} {}
        ~StatementPlaceHolder() {
            UASSERT_OBJ(m_stmtp->backp(), m_stmtp,
                        "Placeholder statement never used - maybe it is unnecessary?");
            m_stmtp->unlinkFrBack()->deleteTree();
        }
        AstNodeStmt* stmtp() const { return m_stmtp; }
    };

    // Takes expression or AstVar and creates a new temporary variable
    AstVar* createTmp(AstNode* const nodep) {
        UASSERT_OBJ(
            VN_IS(nodep, NodeExpr) || VN_IS(nodep, Var), nodep,
            "This function shall only be called on expressions or variables, but was called on: "
                << nodep);
        UASSERT_OBJ(m_currentTmpSpotp, nodep, "No where to place tmp variable");
        AstNodeDType* const dtypep = nodep->dtypep();
        auto& pool = m_tmpUnusedVarps[dtypep->numeric().isSigned() ? 1 : 0];
        if (!pool[dtypep->width()].empty()) {
            AstVar* varp = pool[dtypep->width()].back();
            pool[dtypep->width()].pop_back();
            return varp;
        }
        AstVar* const varp = new AstVar{nodep->fileline(), VVarType::STMTTEMP,
                                        m_tmpNames.get(nodep), VFlagBitPacked{}, nodep->width()};
        m_currentTmpSpotp->addHereThisAsNext(varp);
        varp->funcLocal(m_tmpFuncLocal);
        varp->noSubst(true);
        m_tmpVarpsInUse.push_back(varp);
        return varp;
    }

    static AstNodeDType* getTwoStateDtype(AstNodeDType* dtypepp) {
        AstNodeDType* const dtypep = dtypepp->skipRefp();
        AstNodeDType* resultp = VN_AS(dtypep->user1p(), NodeDType);
        if (resultp) return resultp;
        if (AstUnpackArrayDType* const arrayDtypep = VN_CAST(dtypep, UnpackArrayDType)) {
            AstUnpackArrayDType* const newp = arrayDtypep->cloneTree(false);
            newp->refDTypep(getTwoStateDtype(arrayDtypep->virtRefDTypep()));
            resultp = newp;
        } else if (AstPackArrayDType* const packArrayDtypep = VN_CAST(dtypep, PackArrayDType)) {
            AstPackArrayDType* const newp = packArrayDtypep->cloneTree(false);
            newp->refDTypep(getTwoStateDtype(packArrayDtypep->subDTypep()));
            resultp = newp;
        } else if (AstDynArrayDType* const dynArrayDTypep = VN_CAST(dtypep, DynArrayDType)) {
            AstDynArrayDType* const newp = dynArrayDTypep->cloneTree(false);
            newp->refDTypep(getTwoStateDtype(dynArrayDTypep->subDTypep()));
            resultp = newp;
        } else if (const AstBasicDType* const basicp = VN_CAST(dtypep, BasicDType)) {
            return dtypep->findBitDType(basicp->width(), basicp->widthMin(), basicp->numeric());
        } else if (const AstStructDType* const structDtypep = VN_CAST(dtypep, StructDType)) {
            // Packed structs are bit vectors; two-state equivalent is a basic bit type
            return dtypep->findBitDType(structDtypep->width(), structDtypep->widthMin(),
                                        structDtypep->numeric());
        }
        UASSERT_OBJ(resultp, dtypep, "Failed to split dtype");
        v3Global.rootp()->typeTablep()->addTypesp(resultp);
        dtypep->user1p(resultp);
        return resultp;
    }

    void splitVar(AstVar* const varp) {
        UASSERT_OBJ(needsSplitting(varp->dtypep()), varp,
                    "Split shall be called only on four-state variables");
        if (getValuePartVarp(varp)) return;
        m_varpsToRemove.push_back(varp);
        if (AstNodeFTask* const ftaskp = VN_CAST(varp->backp(), NodeFTask)) {
            if (ftaskp->fvarp() == varp) {
                AstVar* const portEndp = getFTaskPortHelper(ftaskp).lastp();
                AstVar* const returnValuep = new AstVar{varp->fileline(), VVarType::PORT,
                                                        varp->name() + FOURSTATE_VALUE_SUFFIX,
                                                        getTwoStateDtype(varp->dtypep())};
                AstVar* const returnXzp = new AstVar{varp->fileline(), VVarType::PORT,
                                                     varp->name() + FOURSTATE_XZ_SUFFIX,
                                                     getTwoStateDtype(varp->dtypep())};
                returnValuep->direction(VDirection::OUTPUT);
                returnXzp->direction(VDirection::OUTPUT);
                returnValuep->funcLocal(true);
                returnXzp->funcLocal(true);
                returnValuep->lifetime(VLifetime::AUTOMATIC_IMPLICIT);
                returnXzp->lifetime(VLifetime::AUTOMATIC_IMPLICIT);
                returnValuep->trace(varp->isTrace());
                if (const AstBasicDType* const basicp = varp->dtypep()->basicp()) {
                    returnValuep->fourstateOriginalDTypeKwd(basicp->keyword());
                    returnXzp->fourstateOriginalDTypeKwd(basicp->keyword());
                }
                FileLine* const flp = varp->fileline();
                // CReset is not used because V3Task may inline function call and then CReset will
                // be assigned to tmp variable - which does not contain information whether it is
                // used as an complement or what
                AstConst* const constp
                    = new AstConst{flp, AstConst::DTyped{}, returnXzp->dtypep()};
                constp->num().setAllBits1();
                AstAssign* const valueResetp
                    = new AstAssign{flp, new AstVarRef{flp, returnValuep, VAccess::WRITE},
                                    constp->cloneTree(false)};
                AstAssign* const xzResetp
                    = new AstAssign{flp, new AstVarRef{flp, returnXzp, VAccess::WRITE}, constp};
                if (portEndp) {
                    portEndp->addNextHere(xzResetp);
                    portEndp->addNextHere(valueResetp);
                    portEndp->addNextHere(returnXzp);
                    portEndp->addNextHere(returnValuep);
                } else if (AstNode* const stmtp = ftaskp->stmtsp()) {
                    stmtp->addHereThisAsNext(returnValuep);
                    stmtp->addHereThisAsNext(returnXzp);
                    stmtp->addHereThisAsNext(valueResetp);
                    stmtp->addHereThisAsNext(xzResetp);
                } else {
                    ftaskp->addStmtsp(returnValuep);
                    ftaskp->addStmtsp(returnXzp);
                    ftaskp->addStmtsp(valueResetp);
                    ftaskp->addStmtsp(xzResetp);
                }
                FourstateLogicTypePropagator{ftaskp};
                setValuePartVarp(varp, returnValuep);
                returnValuep->fourstateComplementp(returnXzp);
                ftaskp->dtypeSetVoid();
                return;
            }
        }
        AstVar* const newXzp = varp->cloneTree(false);
        newXzp->name(newXzp->name() + FOURSTATE_XZ_SUFFIX);
        if (varp->isPullup() || varp->isPulldown()) {
            // The implicit pull drives a known value, so its unknown-bit mask
            // defaults to zero even when the value half has a pull-up.
            newXzp->pullDirection(false);
        }
        if (const AstBasicDType* const basicp = varp->dtypep()->basicp()) {
            newXzp->fourstateOriginalDTypeKwd(basicp->keyword());
        }
        newXzp->dtypep(getTwoStateDtype(varp->dtypep()));
        if (AstNodeExpr* const valuep = VN_CAST(newXzp->valuep(), NodeExpr)) {
            pushDeletep(valuep->unlinkFrBack());
            newXzp->valuep(getFourstateExpressionXZ(valuep));
        }
        varp->addNextHere(newXzp);
        AstVar* const newValuep = varp->cloneTree(false);
        newValuep->name(newValuep->name() + FOURSTATE_VALUE_SUFFIX);
        newValuep->trace(varp->isTrace());
        if (const AstBasicDType* const basicp = varp->dtypep()->basicp()) {
            newValuep->fourstateOriginalDTypeKwd(basicp->keyword());
        }
        newValuep->dtypep(getTwoStateDtype(varp->dtypep()));
        if (AstNodeExpr* const valuep = VN_CAST(newValuep->valuep(), NodeExpr)) {
            pushDeletep(valuep->unlinkFrBack());
            newValuep->valuep(getFourstateExpressionValue(valuep));
        }
        newValuep->fourstateComplementp(newXzp);
        varp->addNextHere(newValuep);
        setValuePartVarp(varp, newValuep);
    }
    static AstVar* getSplittedValue(AstVar* const varp) {
        UASSERT_OBJ(needsSplitting(varp->dtypep()), varp,
                    "Split shall be called only on four-state variables");
        AstVar* const result = getValuePartVarp(varp);
        UASSERT_OBJ(result, varp, "Variable shall be split first");
        return result;
    }
    static AstVar* getSplittedXZ(AstVar* const varp) {
        return getSplittedValue(varp)->fourstateComplementp();
    }
    const FTaskPortsHelper& getFTaskPortHelper(AstNodeFTask* const ftaskp) {
        if (ftaskp->user1()) return m_ftaskPortHelpers[ftaskp->user1() - 1];
        ftaskp->user1(m_ftaskPortHelpers.size() + 1);
        m_ftaskPortHelpers.emplace_back(static_cast<const AstNodeFTask*>(ftaskp));
        return m_ftaskPortHelpers.back();
    }
    void addPrecalculation(AstNode* const nodep) {
        FourstateLogicTypePropagator{nodep};
        m_currentStmtp->addHereThisAsNext(nodep);
    }
    // This is meant to be used instead of addNextHere for statements
    // This functions extends lifetime of tmp variables
    void addNextCalculation(AstNode* const nodep) {
        UASSERT_OBJ(!VN_IS(nodep, NodeExpr), nodep,
                    "This is meant for nodes that may be placed in statement context");
        UASSERT_OBJ(!m_tmpVarReleaserStack.empty(), nodep,
                    "m_tmpVarReleaserStack shall not be empty when cleup is being added");
        FourstateLogicTypePropagator{nodep};
        m_lastCalculationStatp->addNextHere(nodep);
        m_tmpVarReleaserStack.back().first = nodep;
        m_lastCalculationStatp = nodep;
    }

    AstVar* capturePullPart(AstNodeExpr* const exprp) {
        AstVar* const varp = new AstVar{exprp->fileline(), VVarType::STMTTEMP,
                                        m_tmpNames.get(exprp), getTwoStateDtype(exprp->dtypep())};
        varp->noSubst(true);
        m_modp->addStmtsp(varp);
        addPrecalculation(new AstAssign{
            exprp->fileline(), new AstVarRef{exprp->fileline(), varp, VAccess::WRITE}, exprp});
        return varp;
    }

    FourstatePair applyImplicitPull(AstNodeExpr* const rhsp, const bool pullup) {
        FileLine* const flp = rhsp->fileline();
        // Both halves and the Z mask must be sampled before either target half is written.
        // Generating the halves once also preserves calls with side effects in the RHS.
        AstNodeExpr* const valuep = getOnceExpressionValue(rhsp);
        AstNodeExpr* const xzp = getFourstateExpressionXZ(rhsp);
        // Keep captures distinct across continuous processes; these are not statement-pool temps.
        AstVar* const valueVarp = capturePullPart(valuep);
        AstVar* const xzVarp = capturePullPart(xzp);
        AstNodeExpr* const zp
            = new AstAnd{flp, new AstVarRef{flp, xzVarp, VAccess::READ},
                         new AstNot{flp, new AstVarRef{flp, valueVarp, VAccess::READ}}};
        AstVar* const zVarp = capturePullPart(zp);
        AstNodeExpr* const capturedValuep = new AstVarRef{flp, valueVarp, VAccess::READ};
        AstNodeExpr* const capturedZp = new AstVarRef{flp, zVarp, VAccess::READ};
        const FourstatePair result{
            pullup ? static_cast<AstNodeExpr*>(new AstOr{flp, capturedValuep, capturedZp})
                   : static_cast<AstNodeExpr*>(
                         new AstAnd{flp, capturedValuep, new AstNot{flp, capturedZp}}),
            new AstAnd{flp, new AstVarRef{flp, xzVarp, VAccess::READ},
                       new AstNot{flp, new AstVarRef{flp, zVarp, VAccess::READ}}}};
        // The original assignment is revisited below, including its newly replaced RHS.
        FourstateLogicTypePropagator{result.valuep};
        FourstateLogicTypePropagator{result.xzp};
        return result;
    }

    AstNodeExpr* getOnceExpressionValue(AstNodeExpr* const exprp) {
        if (isFourstate(exprp) || exprp->isPure()) {
            return getFourstateExpressionValue(exprp, true);
        }
        if (AstNodeExpr* const cachedp = getExprValuep(exprp)) {
            return cachedp->cloneTree(false);
        }
        // Both halves must share side effects, including operands used only for their X/Z part.
        FileLine* const flp = exprp->fileline();
        AstNodeExpr* const valuep = getFourstateExpressionValue(exprp, false);
        AstVar* const varp = createTmp(exprp);
        varp->dtypep(getTwoStateDtype(exprp->dtypep()));
        addPrecalculation(new AstAssign{flp, new AstVarRef{flp, varp, VAccess::WRITE}, valuep});
        AstVarRef* const resultp = new AstVarRef{flp, varp, VAccess::READ};
        setFourstate(resultp, false);
        setExprValuep(exprp, resultp);
        return resultp;
    }

    AstNodeExpr* getMemberReceiver(const AstMemberSel* const memberSelp) {
        AstNodeExpr* const fromp = memberSelp->fromp();
        if (fromp->isPure()) return getFourstateExpressionValue(fromp, false);
        if (AstNodeExpr* const cachedp = getExprValuep(fromp)) {
            AstVarRef* const refp = VN_AS(cachedp->cloneTree(false), VarRef);
            refp->access(memberSelp->access());
            return refp;
        }
        // The value and X/Z members must select from the same class handle. Keep this
        // typed temporary outside the integral temporary pool, and preserve the lvalue
        // access convention used by V3LiftExpr for a member selected from a call.
        FileLine* const flp = fromp->fileline();
        AstVar* const varp
            = new AstVar{flp, VVarType::STMTTEMP, m_tmpNames.get(memberSelp), fromp->dtypep()};
        varp->funcLocal(m_tmpFuncLocal);
        varp->noReset(true);
        varp->noSubst(true);
        m_currentTmpSpotp->addHereThisAsNext(varp);
        addPrecalculation(new AstAssign{flp, new AstVarRef{flp, varp, VAccess::WRITE},
                                        getFourstateExpressionValue(fromp, false)});
        AstVarRef* const refp = new AstVarRef{flp, varp, memberSelp->access()};
        setFourstate(refp, false);
        setExprValuep(fromp, refp);
        return refp;
    }

    static bool isIntegralArrayElement(const AstArraySel* const selp) {
        const AstNodeDType* const dtypep = selp->dtypep()->skipRefp();
        return !VN_IS(dtypep, UnpackArrayDType) && !dtypep->isCompound()
               && dtypep->basicp()->keyword().isIntNumeric();
    }

    static bool isFixedIntegralArraySel(const AstArraySel* const selp) {
        if (!VN_IS(selp->fromp()->dtypep()->skipRefp(), UnpackArrayDType)) return false;
        const AstArraySel* leafp = selp;
        // A subarray needs a typed default value. Only handle it as part of a scalar selection.
        while (VN_IS(leafp->dtypep()->skipRefp(), UnpackArrayDType)) {
            const AstArraySel* const parentp = VN_CAST(leafp->backp(), ArraySel);
            if (!parentp || parentp->fromp() != leafp) return false;
            leafp = parentp;
        }
        return isIntegralArrayElement(leafp);
    }

    const ArrayIndexCapture& getArrayIndexCapture(AstArraySel* const selp) {
        const auto it = m_arrayIndexCaptures.find(selp);
        if (it != m_arrayIndexCaptures.end()) return it->second;
        FileLine* const flp = selp->fileline();
        AstNodeExpr* const bitp = selp->bitp();
        static constexpr int minIndexWidth = 64;
        const int width = std::max(minIndexWidth, bitp->width());
        AstNodeExpr* valuep = getOnceExpressionValue(bitp);
        if (valuep->width() < width) {
            valuep = bitp->isSigned()
                         ? static_cast<AstNodeExpr*>(new AstExtendS{flp, valuep, width})
                         : static_cast<AstNodeExpr*>(new AstExtend{flp, valuep, width});
        }
        valuep->dtypeSetBitSized(width, VSigning::UNSIGNED);
        AstVar* const valueVarp = createTmp(valuep);
        valueVarp->dtypep(valuep->dtypep());
        addPrecalculation(
            new AstAssign{flp, new AstVarRef{flp, valueVarp, VAccess::WRITE}, valuep});

        // V3WidthSel already normalized the declaration's low bound, including ascending ranges.
        const AstUnpackArrayDType* const dtypep
            = VN_AS(selp->fromp()->dtypep()->skipRefp(), UnpackArrayDType);
        AstNodeExpr* const badp
            = new AstOr{flp, new AstRedOr{flp, getFourstateExpressionXZ(bitp)},
                        new AstGte{flp, new AstVarRef{flp, valueVarp, VAccess::READ},
                                   new AstConst{flp, AstConst::WidthedValue{}, width,
                                                static_cast<uint32_t>(dtypep->elementsConst())}}};
        AstVar* const badVarp = createTmp(badp);
        addPrecalculation(new AstAssign{flp, new AstVarRef{flp, badVarp, VAccess::WRITE}, badp});
        return m_arrayIndexCaptures.emplace(selp, ArrayIndexCapture{valueVarp, badVarp})
            .first->second;
    }

    static AstNodeExpr* newArrayIndexValue(AstArraySel* const selp,
                                           const ArrayIndexCapture& capture) {
        FileLine* const flp = selp->fileline();
        AstNodeExpr* resultp = new AstVarRef{flp, capture.valuep, VAccess::READ};
        // Bounds use the full snapshot; an in-range array address always fits in 64 bits.
        static constexpr int addressWidth = 64;
        if (resultp->width() > addressWidth) {
            resultp = new AstSel{flp, resultp, 0, addressWidth};
            resultp->dtypeSetBitSized(addressWidth, VSigning::UNSIGNED);
            setSelpHandled(resultp);
        }
        return resultp;
    }

    AstNodeExpr* getArrayReadBad(AstArraySel* const selp) {
        AstNodeExpr* resultp = nullptr;
        for (AstArraySel* currentp = selp; currentp;
             currentp = VN_CAST(currentp->fromp(), ArraySel)) {
            if (!isFixedIntegralArraySel(currentp)) break;
            const ArrayIndexCapture& capture = getArrayIndexCapture(currentp);
            AstNodeExpr* const badp
                = new AstVarRef{currentp->fileline(), capture.badp, VAccess::READ};
            resultp = resultp ? new AstOr{selp->fileline(), resultp, badp} : badp;
        }
        return resultp;
    }

    AstNodeExpr* getFourstateExpressionArraySelHandler(AstArraySel* const selp,
                                                       const bool xzPart) {
        FileLine* const flp = selp->fileline();
        if (!isFixedIntegralArraySel(selp)) {
            // Whole subarrays and other element types retain their existing lowering.
            selp->bitp()->purityCheck();
            AstArraySel* const resultp
                = new AstArraySel{flp,
                                  xzPart ? getFourstateExpressionXZ(selp->fromp())
                                         : getFourstateExpressionValue(selp->fromp()),
                                  isFourstate(selp->bitp()) ? getTwoStateCast(selp->bitp())
                                                            : selp->bitp()->cloneTree(false)};
            resultp->dtypep(getTwoStateDtype(selp->dtypep()));
            setSelpHandled(resultp);
            return resultp;
        }
        AstNodeExpr* const fromp = [&]() -> AstNodeExpr* {
            if (AstArraySel* const parentp = VN_CAST(selp->fromp(), ArraySel)) {
                if (isFixedIntegralArraySel(parentp)) {
                    return getFourstateExpressionArraySelHandler(parentp, xzPart);
                }
            }
            return xzPart ? getFourstateExpressionXZ(selp->fromp())
                          : getFourstateExpressionValue(selp->fromp());
        }();
        const ArrayIndexCapture& capture = getArrayIndexCapture(selp);
        AstNodeExpr* indexp = newArrayIndexValue(selp, capture);
        const AstNode* const basep = selp->fromp()->baseFromp(false);
        const AstNodeVarRef* const varrefp = VN_CAST(basep, NodeVarRef);
        const AstMemberSel* const memberSelp = VN_CAST(basep, MemberSel);
        const bool lvalue = (varrefp && varrefp->access().isWriteOrRW())
                            || (memberSelp && memberSelp->access().isWriteOrRW());
        const bool leaf = isIntegralArrayElement(selp);
        if (lvalue || !leaf) {
            AstConst* const invalidp
                = new AstConst{flp, AstConst::WidthedValue{}, indexp->width(), 0U};
            // The wide sentinel lets V3Unknown guard writes and retain RHS side effects/timing.
            if (lvalue) invalidp->num().setAllBits1();
            indexp = new AstCond{flp, new AstVarRef{flp, capture.badp, VAccess::READ}, invalidp,
                                 indexp};
        }
        AstArraySel* const resultp = new AstArraySel{flp, fromp, indexp};
        resultp->dtypep(getTwoStateDtype(selp->dtypep()));
        setSelpHandled(resultp);
        if (lvalue || !leaf) return resultp;
        return new AstCond{flp, getArrayReadBad(selp), createZeroOrOnesp(selp, isFourstate(selp)),
                           resultp};
    }

    AstNodeExpr* getFourstateExpressionSelHandler(AstSel* const selp,
                                                  AstNodeExpr* const valueExprp,
                                                  const bool defaultsToZero) {
        // In two-state mode boundary checks are handled in V3Unknown
        FileLine* const flp = selp->fileline();
        const AstNode* const basep = selp->fromp()->baseFromp(false);
        const AstNodeVarRef* const varrefp = VN_CAST(basep, NodeVarRef);
        const AstMemberSel* const memberSelp = VN_CAST(basep, MemberSel);
        const bool lvalue = (varrefp && varrefp->access().isWriteOrRW())
                            || (memberSelp && memberSelp->access().isWriteOrRW());
        if (lvalue) {
            AstNodeExpr* const lsbp = selp->lsbp()->unlinkFrBack();
            AstNodeExpr* const fromp = selp->fromp()->unlinkFrBack();
            AstSel* const newp = selp->cloneTree(false);
            selp->lsbp(lsbp);
            selp->fromp(fromp);
            if (isFourstate(lsbp)) {
                auto assureWidth = [flp, minWidth = std::max(64, lsbp->width())](
                                       AstNodeExpr* const exprp) -> AstNodeExpr* {
                    UASSERT_OBJ(exprp->width() <= minWidth, exprp,
                                "This function shall only expand values");
                    if (exprp->width() < minWidth) return new AstExtend{flp, exprp};
                    return exprp;
                };
                // The assumption is that no signal/array will ever have 2^64 indexes so,
                // V3Unknown will handle x/z
                AstConst* const constp = new AstConst{flp, 0};
                constp->dtypeSetBitSized(64, VSigning::UNSIGNED);
                constp->num().setAllBits1();
                newp->lsbp(new AstCond{
                    flp, new AstNeq{flp, getFourstateExpressionXZ(lsbp), createZeroOrOnesp(lsbp)},
                    assureWidth(constp), assureWidth(getFourstateExpressionValue(lsbp))});
            } else {
                newp->lsbp(getOnceExpressionValue(lsbp));
            }
            newp->fromp(valueExprp);
            { FourstateLogicTypePropagator{newp}; }
            return newp;
        }
        AstNodeExpr* lsbp = selp->lsbp();
        V3Number maxmsb{flp, 32, static_cast<uint32_t>(selp->fromp()->dtypep()->width() - 1)};
        if (isStaticlyNGte(maxmsb, lsbp)) {
            if (!selp->fromp()->isPure()) {
                addPrecalculation(new AstStmtExpr{flp, valueExprp});
                // No precalculation of lsbp because right now:
                // isStaticlyNGte(lsbp) => VN_IS(lsbp, Const)
            } else {
                pushDeletep(valueExprp);
            }
            return createZeroOrOnesp(selp, !defaultsToZero);
        }
        AstSel* const newp = [selp] {
            AstNodeExpr* const fromp = selp->fromp()->unlinkFrBack();
            AstNodeExpr* const lsbp = selp->lsbp()->unlinkFrBack();
            AstSel* const newp = selp->cloneTree(false);
            selp->fromp(fromp);
            selp->lsbp(lsbp);
            return newp;
        }();
        setSelpHandled(newp);
        newp->fromp(valueExprp);
        const bool isStaticlyInRange = V3Unknown::isStaticlyGte(maxmsb, lsbp);
        const bool isLsbpFourstate = isFourstate(lsbp);
        if (isStaticlyInRange && !isLsbpFourstate) {
            newp->lsbp(lsbp->cloneTree(false));
            return newp;
        }
        AstNodeExpr* conditionp;
        if (isLsbpFourstate) {
            conditionp = getFourstateExpressionXZ(lsbp, isFourstate(selp));
            if (!isStaticlyInRange) {
                conditionp = new AstOr{flp, conditionp,
                                       new AstLt{flp, new AstConst{flp, maxmsb},
                                                 getFourstateExpressionValue(lsbp, true)}};
            }
            lsbp = getFourstateExpressionValue(lsbp, true);
        } else {
            if (!VN_IS(lsbp,
                       NodeVarRef) /*&& !VN_IS(lsbp, Const)*/) {  // Not being a Const is
                                                                  // guaranteed by logic above - if
                                                                  // lsbp is a AstConst then it is
                                                                  // either statically inside or
                                                                  // outside range
                AstVar* const lsbTmpp = createTmp(lsbp);
                addPrecalculation(new AstAssign{flp, new AstVarRef{flp, lsbTmpp, VAccess::WRITE},
                                                lsbp->cloneTree(false)});
                lsbp = new AstVarRef{flp, lsbTmpp, VAccess::READ};
            } else {
                lsbp = lsbp->cloneTree(false);
            }
            conditionp = new AstLt{flp, new AstConst{flp, maxmsb}, lsbp->cloneTree(false)};
        }
        newp->lsbp(lsbp);
        return new AstCond{flp, conditionp, createZeroOrOnesp(selp, !defaultsToZero), newp};
    }

    // Base visitor for Value and XZ visitor, contains some common functionalities
    class FourstateExpressionVisitor VL_NOT_FINAL : public VNVisitor {
    protected:
        FourstateVisitor& m_fourstateVisitor;  // Reference to the FourstateVisitor
        AstNodeExpr* m_resultp = nullptr;  // Result of a call to get()

    private:
        bool m_noTmp = false;  // Do not put result into temporary variable
        bool m_enforceTmp = false;  // Enforce putting expression into temporary variable

        virtual AstNodeExpr* getCache(const AstNodeExpr* keyp) = 0;
        virtual void setCache(AstNodeExpr* keyp, AstNodeExpr* valuep) = 0;

    protected:
        void noTmp() { m_noTmp = true; }
        void enforceTmp() { m_enforceTmp = true; }

        void addPrecalculation(AstNode* const nodep) {
            m_fourstateVisitor.addPrecalculation(nodep);
        }

        template <typename T_Shift>
        AstNodeExpr* newFourstateShift(AstNodeBiop* const nodep, const bool xzPart) {
            FileLine* const flp = nodep->fileline();
            AstNodeExpr* lhsp = m_fourstateVisitor.getOnceExpressionValue(nodep->lhsp());
            if (xzPart) {
                // The value must still run when only the X/Z half is used or the count is unknown.
                pushDeletep(lhsp);
                lhsp = getFourstateExpressionXZ(nodep->lhsp(), false);
            }
            AstNodeExpr* const rhsp = m_fourstateVisitor.getOnceExpressionValue(nodep->rhsp());
            T_Shift* const shiftp = new T_Shift{flp, lhsp, rhsp};
            shiftp->dtypep(getTwoStateDtype(nodep->dtypep()));
            // Arithmetic shifts extend the sign bit of both halves, including an X/Z sign bit.
            return new AstCond{flp, new AstRedOr{flp, getFourstateExpressionXZ(nodep->rhsp())},
                               createZeroOrOnesp(nodep, true), shiftp};
        }

        void liftExprStmtStatements(AstExprStmt* const exprStmtp) {
            AstNode* stmtsp = exprStmtp->stmtsp();
            if (!stmtsp) return;
            stmtsp = stmtsp->unlinkFrBackWithNext();
            while (stmtsp) {
                AstNode* const nextp = stmtsp->nextp();
                if (nextp) nextp->unlinkFrBack();
                AstNodeStmt* const stmtp = VN_AS(stmtsp, NodeStmt);
                m_fourstateVisitor.m_currentStmtp->addHereThisAsNext(stmtp);
                m_fourstateVisitor.iterate(stmtp);
                stmtsp = nextp;
            }
        }

        void fourstateExpressionFuncRefHandler(AstNodeFTaskRef* const funcRefp) {
            // Its ok to use this instead of output since we only need width which is the same
            AstVar* const functionReturnVarp = VN_AS(VN_AS(funcRefp->taskp(), Func)->fvarp(), Var);
            AstVar* const resultValuep = m_fourstateVisitor.createTmp(functionReturnVarp);
            AstVar* const resultXzp = m_fourstateVisitor.createTmp(functionReturnVarp);
            AstNodeFTaskRef* const newCallp = funcRefp->cloneTree(false);
            UASSERT_OBJ(!isFTaskRefHandled(newCallp), funcRefp,
                        "Trying to handle already handled four-state function call");
            setFTaskRefHandled(newCallp);
            if (newCallp->argsp()) pushDeletep(newCallp->argsp()->unlinkFrBackWithNext());
            FileLine* const flp = funcRefp->fileline();
            {
                size_t argIdx = 0;
                const FTaskPortsHelper& ftaskPortsHelper
                    = m_fourstateVisitor.getFTaskPortHelper(funcRefp->taskp());
                for (AstArg* argp = funcRefp->argsp(); argp; argp = VN_AS(argp->nextp(), Arg)) {
                    const AstVar* const varp
                        = ftaskPortsHelper.getArgPortVar(argp->name(), argIdx);
                    ++argIdx;
                    if (needsSplitting(varp->dtypep())) {
                        newCallp->addArgsp(new AstArg{
                            flp, "", getFourstateExpressionValue(argp->exprp(), false)});
                        newCallp->addArgsp(
                            new AstArg{flp, "", getFourstateExpressionXZ(argp->exprp(), false)});
                    } else if (isFourstate(argp->exprp())) {
                        newCallp->addArgsp(new AstArg{
                            flp, "", m_fourstateVisitor.getTwoStateCast(argp->exprp())});
                    } else {
                        newCallp->addArgsp(argp->cloneTree(false));
                    }
                }
            }
            AstVarRef* const resultValueRefp = new AstVarRef{flp, resultValuep, VAccess::WRITE};
            AstVarRef* const resultXzRefp = new AstVarRef{flp, resultXzp, VAccess::WRITE};
            setFourstate(resultValueRefp, false);
            setFourstate(resultXzRefp, false);
            {
                std::string resultName = funcRefp->taskp()->fvarp()->name();
                AstArg* const resultValueArgp
                    = new AstArg{flp, resultName + FOURSTATE_VALUE_SUFFIX, resultValueRefp};
                AstArg* const resultXZArgp
                    = new AstArg{flp, std::move(resultName) + FOURSTATE_XZ_SUFFIX, resultXzRefp};
                newCallp->addArgsp(resultValueArgp);
                newCallp->addArgsp(resultXZArgp);
            }
            AstStmtExpr* const newStmtExprp = new AstStmtExpr{flp, newCallp};
            addPrecalculation(newStmtExprp);
            AstVarRef* const varRefValuep = new AstVarRef{flp, resultValuep, VAccess::READ};
            AstVarRef* const varRefXzp = new AstVarRef{flp, resultXzp, VAccess::READ};
            pushDeletep(varRefValuep);
            pushDeletep(varRefXzp);
            setExprValuep(funcRefp, varRefValuep);
            setExprXZp(funcRefp, varRefXzp);
        }
        void fourstateExpressionCondHandler(AstCond* const condp) {
            // a ? b : c
            // if (a.xz) {
            //   resultXzp    = (b.value ^ c.value) | (b.xz | c.xz);
            //   resultValuep = resultXzp | b.value;  // `b.value` is chosen arbitrary - it could
            //   // be `c.value`
            //   // `resultXzp | b.value <=> (b.xz | c.xz) | (b.value | c.value)`
            // } else if (a.value) {
            //   resultValuep = b.value;
            //   resultXzp    = b.xz;
            // } else {
            //   resultValuep = c.value;
            //   resultXzp    = c.xz;
            // }
            // In case when `a` is a two-state value first `if` is omitted
            // and its `else` branch is used instead
            UASSERT_OBJ(condp->thenp()->dtypep()->skipRefp()->isIntegralOrPacked(), condp,
                        "This function should only handle conds that result with a integral type");
            UASSERT_OBJ(condp->elsep()->dtypep()->skipRefp()->isIntegralOrPacked(), condp,
                        "This function should only handle conds that result with a integral type");
            FileLine* const flp = condp->fileline();
            AstVar* const resultValueTmpVarp = m_fourstateVisitor.createTmp(condp->thenp());
            AstVar* const resultXZTmpVarp = m_fourstateVisitor.createTmp(condp->thenp());
            AstIf* ifp = new AstIf{flp, isFourstate(condp->condp())
                                            ? getFourstateExpressionXZ(condp->condp())
                                            : condp->condp()->cloneTree(false)};
            // Those must be here so expr is always evaluated fully in the right place
            AstIf* twoStateIfp = ifp;
            if (isFourstate(condp->condp())) {
                // Condition is X/Z
                AstNodeExpr* conditionValuep = getFourstateExpressionValue(condp->condp());
                AstNodeExpr* const thenCopyp = condp->thenp()->cloneTree(false);
                AstNodeExpr* const elseCopyp = condp->elsep()->cloneTree(false);
                StatementPlaceHolder thenPlaceholder{m_fourstateVisitor, flp};
                ifp->addThensp(thenPlaceholder.stmtp());
                addPrecalculation(new AstAssign{
                    flp, new AstVarRef{flp, resultXZTmpVarp, VAccess::WRITE},
                    new AstOr{flp,
                              new AstXor{flp, getFourstateExpressionValue(thenCopyp, true),
                                         getFourstateExpressionValue(elseCopyp, false)},
                              new AstOr{flp, getFourstateExpressionXZ(thenCopyp, false),
                                        getFourstateExpressionXZ(elseCopyp, false)}}});
                addPrecalculation(
                    new AstAssign{flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::WRITE},
                                  new AstOr{flp, getFourstateExpressionValue(thenCopyp, true),
                                            new AstVarRef{flp, resultXZTmpVarp, VAccess::READ}}});
                thenCopyp->deleteTree();
                elseCopyp->deleteTree();
                twoStateIfp = new AstIf{flp, conditionValuep};
                ifp->addElsesp(twoStateIfp);
            }
            {
                // Condition is 1/0
                {
                    // Condition is 1
                    StatementPlaceHolder thenPlaceholder{m_fourstateVisitor, flp};
                    twoStateIfp->addThensp(thenPlaceholder.stmtp());
                    addPrecalculation(
                        new AstAssign{flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::WRITE},
                                      getFourstateExpressionValue(condp->thenp(), false)});
                    addPrecalculation(
                        new AstAssign{flp, new AstVarRef{flp, resultXZTmpVarp, VAccess::WRITE},
                                      getFourstateExpressionXZ(condp->thenp(), false)});
                }
                {
                    // Condition is 0
                    StatementPlaceHolder elsePlaceholder{m_fourstateVisitor, flp};
                    twoStateIfp->addElsesp(elsePlaceholder.stmtp());
                    addPrecalculation(
                        new AstAssign{flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::WRITE},
                                      getFourstateExpressionValue(condp->elsep(), false)});
                    addPrecalculation(
                        new AstAssign{flp, new AstVarRef{flp, resultXZTmpVarp, VAccess::WRITE},
                                      getFourstateExpressionXZ(condp->elsep(), false)});
                }
            }
            addPrecalculation(ifp);
            AstVarRef* const resultValueTmpVarRefp
                = new AstVarRef{flp, resultValueTmpVarp, VAccess::READ};
            AstVarRef* const resultXZTmpVarRefp
                = new AstVarRef{flp, resultXZTmpVarp, VAccess::READ};
            pushDeletep(resultValueTmpVarRefp);
            pushDeletep(resultXZTmpVarRefp);
            setExprValuep(condp, resultValueTmpVarRefp);
            setExprXZp(condp, resultXZTmpVarRefp);
        }
        void fourstateExpressionLogAndHandler(AstLogAnd* const logAndp) {
            FileLine* const flp = logAndp->fileline();
            AstVar* const resultValueTmpVarp = m_fourstateVisitor.createTmp(logAndp);
            AstVar* const resultXZTmpVarp = m_fourstateVisitor.createTmp(logAndp);
            addPrecalculation(new AstAssign{flp,
                                            new AstVarRef{flp, resultXZTmpVarp, VAccess::WRITE},
                                            getFourstateExpressionXZ(logAndp->lhsp(), false)});
            addPrecalculation(
                new AstAssign{flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::WRITE},
                              new AstOr{flp, new AstVarRef{flp, resultXZTmpVarp, VAccess::READ},
                                        getFourstateExpressionValue(logAndp->lhsp(), false)}});
            AstIf* const ifp
                = new AstIf{flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::READ}};
            addPrecalculation(ifp);
            {
                // Lhs is non zero
                StatementPlaceHolder placeholderStmt{m_fourstateVisitor, flp};
                ifp->addThensp(placeholderStmt.stmtp());
                addPrecalculation(new AstAssign{
                    flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::WRITE},
                    new AstOr{flp, getFourstateExpressionValue(logAndp->rhsp(), false),
                              getFourstateExpressionXZ(logAndp->rhsp())}});
                addPrecalculation(new AstAssign{
                    flp, new AstVarRef{flp, resultXZTmpVarp, VAccess::WRITE},
                    new AstLogAnd{flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::READ},
                                  new AstOr{flp,
                                            new AstVarRef{flp, resultXZTmpVarp, VAccess::READ},
                                            getFourstateExpressionXZ(logAndp->rhsp())}}});
            }
            AstVarRef* const resultValueTmpVarRefp
                = new AstVarRef{flp, resultValueTmpVarp, VAccess::READ};
            AstVarRef* const resultXZTmpVarRefp
                = new AstVarRef{flp, resultXZTmpVarp, VAccess::READ};
            pushDeletep(resultValueTmpVarRefp);
            pushDeletep(resultXZTmpVarRefp);
            setExprValuep(logAndp, resultValueTmpVarRefp);
            setExprXZp(logAndp, resultXZTmpVarRefp);
        }
        void fourstateExpressionLogOrHandler(AstLogOr* const logOrp) {
            FileLine* const flp = logOrp->fileline();
            AstVar* const resultValueTmpVarp = m_fourstateVisitor.createTmp(logOrp);
            AstVar* const resultXZTmpVarp = m_fourstateVisitor.createTmp(logOrp);
            addPrecalculation(new AstAssign{flp,
                                            new AstVarRef{flp, resultXZTmpVarp, VAccess::WRITE},
                                            getFourstateExpressionXZ(logOrp->lhsp(), false)});
            addPrecalculation(new AstAssign{flp,
                                            new AstVarRef{flp, resultValueTmpVarp, VAccess::WRITE},
                                            getFourstateExpressionValue(logOrp->lhsp(), false)});
            AstIf* const ifp = new AstIf{
                flp,
                new AstOr{flp,
                          new AstNot{flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::READ}},
                          new AstVarRef{flp, resultXZTmpVarp, VAccess::READ}}};
            addPrecalculation(ifp);
            {
                // Lhs is non one
                StatementPlaceHolder placeholderStmt{m_fourstateVisitor, flp};
                ifp->addThensp(placeholderStmt.stmtp());
                addPrecalculation(new AstAssign{
                    flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::WRITE},
                    new AstOr{flp, getFourstateExpressionValue(logOrp->rhsp()),
                              new AstOr{flp, getFourstateExpressionXZ(logOrp->rhsp()),
                                        new AstVarRef{flp, resultXZTmpVarp, VAccess::READ}}}});
                addPrecalculation(new AstAssign{
                    flp, new AstVarRef{flp, resultXZTmpVarp, VAccess::WRITE},
                    new AstLogAnd{
                        flp, new AstVarRef{flp, resultValueTmpVarp, VAccess::READ},
                        new AstOr{flp,
                                  new AstNot{flp, getFourstateExpressionValue(logOrp->rhsp())},
                                  getFourstateExpressionXZ(logOrp->rhsp())}}});
            }
            AstVarRef* const resultValueTmpVarRefp
                = new AstVarRef{flp, resultValueTmpVarp, VAccess::READ};
            AstVarRef* const resultXZTmpVarRefp
                = new AstVarRef{flp, resultXZTmpVarp, VAccess::READ};
            pushDeletep(resultValueTmpVarRefp);
            pushDeletep(resultXZTmpVarRefp);
            setExprValuep(logOrp, resultValueTmpVarRefp);
            setExprXZp(logOrp, resultXZTmpVarRefp);
        }

        AstConsDynArray*
        fourstateExpressionConsDynArrayHandler(AstConsDynArray* const consDynArrayp, bool xz) {
            AstNodeExpr* const lhsp
                = consDynArrayp->lhsp() ? consDynArrayp->lhsp()->unlinkFrBack() : nullptr;
            AstNodeExpr* const rhsp
                = consDynArrayp->rhsp() ? consDynArrayp->rhsp()->unlinkFrBack() : nullptr;
            AstConsDynArray* const newp = consDynArrayp->cloneTree(false);
            consDynArrayp->lhsp(lhsp);
            consDynArrayp->rhsp(rhsp);
            if (AstConsDynArray* const cp = VN_CAST(lhsp, ConsDynArray)) {
                newp->lhsp(fourstateExpressionConsDynArrayHandler(cp, xz));
            } else if (lhsp) {
                newp->lhsp(xz ? getFourstateExpressionXZ(lhsp)
                              : getFourstateExpressionValue(lhsp));
            }
            if (AstConsDynArray* const cp = VN_CAST(rhsp, ConsDynArray)) {
                newp->rhsp(fourstateExpressionConsDynArrayHandler(cp, xz));
            } else if (rhsp) {
                newp->rhsp(xz ? getFourstateExpressionXZ(rhsp)
                              : getFourstateExpressionValue(rhsp));
            }
            { FourstateLogicTypePropagator{newp}; }
            return newp;
        }

        void fourstateExpressionCMethodHardHandler(AstCMethodHard* const cMethodHardp) {
            if (cMethodHardp->withp()) {
                cMethodHardp->withp()->v3warn(E_UNSUPPORTED,
                                              "With clausule is unsupported with --fourstate");
            }
            AstNodeExpr* const fromp = cMethodHardp->fromp()->unlinkFrBack();
            AstNodeExpr* pinsp = nullptr;
            if (cMethodHardp->pinsp()) pinsp = cMethodHardp->pinsp()->unlinkFrBackWithNext();
            AstCMethodHard* const valuep = cMethodHardp->cloneTree(false);
            AstCMethodHard* xzp = cMethodHardp->cloneTree(false);
            cMethodHardp->fromp(fromp);
            cMethodHardp->addPinsp(pinsp);
            valuep->fromp(getFourstateExpressionValue(fromp, false));
            xzp->fromp(getFourstateExpressionXZ(fromp, false));
            switch (cMethodHardp->method()) {
            case VCMethod::DYN_RENEW:
            case VCMethod::ARRAY_AT_WRITE:
            case VCMethod::ARRAY_AT: {
                pinsp->purityCheck();
                if (isFourstate(pinsp)) {
                    valuep->addPinsp(m_fourstateVisitor.getTwoStateCast(pinsp));  // FIXME
                    xzp->addPinsp(m_fourstateVisitor.getTwoStateCast(pinsp));  // FIXME
                } else {
                    valuep->addPinsp(pinsp->cloneTree(false));
                    xzp->addPinsp(pinsp->cloneTree(false));
                }
            } break;
            case VCMethod::DYN_RENEW_COPY: {
                pinsp->purityCheck();
                if (isFourstate(pinsp)) {
                    valuep->addPinsp(m_fourstateVisitor.getTwoStateCast(pinsp));  // FIXME
                    xzp->addPinsp(m_fourstateVisitor.getTwoStateCast(pinsp));  // FIXME
                } else {
                    valuep->addPinsp(pinsp->cloneTree(false));
                    xzp->addPinsp(pinsp->cloneTree(false));
                }
                AstNodeExpr* const sourcep = VN_AS(pinsp->nextp(), NodeExpr);
                if (isFourstate(sourcep)) {
                    valuep->addPinsp(getFourstateExpressionValue(sourcep));
                    xzp->addPinsp(getFourstateExpressionXZ(sourcep));
                } else if (AstConsDynArray* const consDynArrayp = VN_CAST(sourcep, ConsDynArray)) {
                    valuep->addPinsp(fourstateExpressionConsDynArrayHandler(consDynArrayp, false));
                    xzp->addPinsp(fourstateExpressionConsDynArrayHandler(consDynArrayp, true));
                } else {
                    sourcep->v3warn(E_UNSUPPORTED, "Copying to 4-state from 2-state");
                    break;
                }
            } break;
            case VCMethod::DYN_CLEAR: break;
            case VCMethod::DYN_SIZE: {
                VL_DO_DANGLING(xzp->deleteTree(), xzp);
                setExprXZp(cMethodHardp, createZeroOrOnesp(cMethodHardp));
            } break;
            default:
                cMethodHardp->v3warn(
                    E_UNSUPPORTED, "Unsupported CMethod hard: " << cMethodHardp->method().ascii());
                break;
            }
            setExprValuep(cMethodHardp, valuep);
            if (xzp) setExprXZp(cMethodHardp, xzp);
        }

        void fourstateExpressionExprStmtHandler(AstExprStmt* const exprStmtp) {
            addPrecalculation(exprStmtp->stmtsp()->cloneTree(true));
            AstNodeExpr* const resultValuep
                = getFourstateExpressionValue(exprStmtp->resultp(), false);
            AstNodeExpr* const resultXzp = getFourstateExpressionXZ(exprStmtp->resultp(), false);
            pushDeletep(resultValuep);
            pushDeletep(resultXzp);
            setExprValuep(exprStmtp, resultValuep);
            setExprXZp(exprStmtp, resultXzp);
        }
        AstNodeExpr* get(AstNodeExpr* const exprp, bool putIntoTmp = true) {
            if (AstNodeExpr* result = getCache(exprp)) return result->cloneTree(false);
            m_resultp = nullptr;
            VL_RESTORER(m_noTmp);
            VL_RESTORER(m_enforceTmp);
            m_noTmp = false;
            m_enforceTmp = false;
            iterate(exprp);
            UASSERT_OBJ(m_resultp, exprp,
                        "Result shall always be returned - even if it is just a place holder");
            UASSERT_OBJ(!(m_noTmp && m_enforceTmp), exprp,
                        "Expression may not enforce and omit tmp variable at the same time");
            if (m_enforceTmp || (putIntoTmp && !m_noTmp)) {
                FileLine* const flp = exprp->fileline();
                AstVar* const varp = m_fourstateVisitor.createTmp(exprp);
                AstVarRef* const varRefp = new AstVarRef{flp, varp, VAccess::WRITE};
                AstAssign* const assignp = new AstAssign{flp, varRefp, m_resultp};
                addPrecalculation(assignp);
                m_resultp = new AstVarRef{flp, varp, VAccess::READ};
                setFourstate(m_resultp, false);
            }
            setCache(exprp, m_resultp);
            return m_resultp;
        }

    public:
        explicit FourstateExpressionVisitor(FourstateVisitor& fourstateVisitor)
            : m_fourstateVisitor{fourstateVisitor} {}
        ~FourstateExpressionVisitor() override = default;

        virtual AstNodeExpr* getFourstateExpressionValue(AstNodeExpr* const exprp,
                                                         bool putIntoTmp = true) {
            return m_fourstateVisitor.m_fourstateGeneratorValueVisitor.getFourstateExpressionValue(
                exprp, putIntoTmp);
        }
        virtual AstNodeExpr* getFourstateExpressionXZ(AstNodeExpr* const exprp,
                                                      const bool putIntoTmp = true) {
            return m_fourstateVisitor.m_fourstateGeneratorXZVisitor.getFourstateExpressionXZ(
                exprp, putIntoTmp);
        }
    };

    // Visitor used to get an expression with a value of a value part of a four-state expression
    // This can be thought as a function - but a Visitor was used to be able to use vtable, create
    // some enclosing namespace and benefit from inheritance
    class FourstateExpressionValueVisitor final : public FourstateExpressionVisitor {

        void visit(AstAnd* const andp) override {
            // (a.value | a.xz) & (b.value | b.xz)
            FileLine* const flp = andp->fileline();
            m_resultp = new AstAnd{flp,
                                   new AstOr{flp, getFourstateExpressionValue(andp->lhsp()),
                                             getFourstateExpressionXZ(andp->lhsp())},
                                   new AstOr{flp, getFourstateExpressionValue(andp->rhsp()),
                                             getFourstateExpressionXZ(andp->rhsp())}};
        }
        void visit(AstOr* const orp) override {
            // a.value | b.value | a.xz | b.xz
            FileLine* const flp = orp->fileline();
            m_resultp = new AstOr{flp,
                                  new AstOr{flp, getFourstateExpressionValue(orp->lhsp()),
                                            getFourstateExpressionValue(orp->rhsp())},
                                  new AstOr{flp, getFourstateExpressionXZ(orp->lhsp()),
                                            getFourstateExpressionXZ(orp->rhsp())}};
        }
        void visit(AstXor* const xorp) override {
            // (a.value ^ b.value) | a.xz | b.xz
            FileLine* const flp = xorp->fileline();
            m_resultp = new AstOr{flp,
                                  new AstXor{flp, getFourstateExpressionValue(xorp->lhsp(), false),
                                             getFourstateExpressionValue(xorp->rhsp(), false)},
                                  getFourstateExpressionXZ(xorp)};
        }
        void visit(AstNot* const notp) override {
            // ~a.value | a.xz
            FileLine* const flp = notp->fileline();
            m_resultp = new AstOr{flp, new AstNot{flp, getFourstateExpressionValue(notp->lhsp())},
                                  getFourstateExpressionXZ(notp->lhsp())};
        }

        void visit(AstLogNot* const logNotp) override {
            FileLine* const flp = logNotp->fileline();
            AstNodeExpr* const knownOnep
                = new AstRedOr{flp, m_fourstateVisitor.getTwoStateCast(logNotp->lhsp())};
            m_resultp = new AstLogNot{flp, knownOnep};
        }

        void visit(AstOneHot* const nodep) override {
            FileLine* const flp = nodep->fileline();

            m_resultp = new AstOneHot{
                flp, new AstAnd{flp, getFourstateExpressionValue(nodep->lhsp(), false),
                                new AstNot{flp, getFourstateExpressionXZ(nodep->lhsp(), false)}}};
        }

        void visit(AstOneHot0* const nodep) override {
            FileLine* const flp = nodep->fileline();

            m_resultp = new AstOneHot0{
                flp, new AstAnd{flp, getFourstateExpressionValue(nodep->lhsp(), false),
                                new AstNot{flp, getFourstateExpressionXZ(nodep->lhsp(), false)}}};
        }

        void visit(AstCountBits* const nodep) override {
            FileLine* const flp = nodep->fileline();
            AstCountBits* const newp
                = new AstCountBits{flp, getFourstateExpressionValue(nodep->lhsp(), false),
                                   getFourstateExpressionValue(nodep->rhsp(), false),
                                   getFourstateExpressionValue(nodep->thsp(), false),
                                   getFourstateExpressionValue(nodep->fhsp(), false)};
            newp->dtypeSetLogicUnsized(32, V3Number::log2b(newp->lhsp()->width()) + 1,
                                       VSigning::SIGNED);
            m_resultp = newp;
        }

        void visit(AstCLog2* const nodep) override {
            FileLine* const flp = nodep->fileline();
            AstCLog2* const clog2p
                = new AstCLog2{flp, getFourstateExpressionValue(nodep->lhsp(), true)};
            m_resultp
                = new AstCond{flp, new AstRedOr{flp, getFourstateExpressionXZ(nodep->lhsp())},
                              createZeroOrOnesp(nodep, true), clog2p};
        }

        template <typename ComparisonOp_T>
        void visitCompare(ComparisonOp_T* const cmpp) {
            // |(a.xz | b.xz) | (a.value op b.value)
            FileLine* const flp = cmpp->fileline();
            m_resultp
                = new AstOr{flp, getFourstateExpressionXZ(cmpp),
                            new ComparisonOp_T{flp, getFourstateExpressionValue(cmpp->lhsp()),
                                               getFourstateExpressionValue(cmpp->rhsp())}};
        }
        void visit(AstEq* const eqp) override { visitCompare(eqp); }
        void visit(AstNeq* const neqp) override { visitCompare(neqp); }
        void visit(AstGt* const gtp) override { visitCompare(gtp); }
        void visit(AstGte* const gtep) override { visitCompare(gtep); }
        void visit(AstLt* const ltp) override { visitCompare(ltp); }
        void visit(AstLte* const ltep) override { visitCompare(ltep); }
        void visit(AstGtS* const gtp) override { visitCompare(gtp); }
        void visit(AstGteS* const gtep) override { visitCompare(gtep); }
        void visit(AstLtS* const ltp) override { visitCompare(ltp); }
        void visit(AstLteS* const ltep) override { visitCompare(ltep); }

        void visit(AstEqWild* const eqWildp) override {
            // ((a.value | b.xz) == (b.value | b.xz)) | |(a.xz & ~b.xz)
            FileLine* const flp = eqWildp->fileline();
            m_resultp = new AstOr{
                flp,
                new AstEq{flp,
                          new AstOr{flp, getFourstateExpressionValue(eqWildp->lhsp(), false),
                                    getFourstateExpressionXZ(eqWildp->rhsp())},
                          new AstOr{flp, getFourstateExpressionValue(eqWildp->rhsp(), false),
                                    getFourstateExpressionXZ(eqWildp->rhsp())}},
                getFourstateExpressionXZ(eqWildp)};
        }
        void visit(AstNeqWild* const neqWildp) override {
            // ((a.value | b.xz) != (b.value | b.xz)) | |(a.xz & ~b.xz)
            FileLine* const flp = neqWildp->fileline();
            m_resultp = new AstOr{
                flp,
                new AstNeq{flp,
                           new AstOr{flp, getFourstateExpressionValue(neqWildp->lhsp(), false),
                                     getFourstateExpressionXZ(neqWildp->rhsp())},
                           new AstOr{flp, getFourstateExpressionValue(neqWildp->rhsp(), false),
                                     getFourstateExpressionXZ(neqWildp->rhsp())}},
                getFourstateExpressionXZ(neqWildp)};
        }

        void visit(AstInsideRange* const insideRangep) override {
            AstNodeExpr* const lhsp = VN_IS(insideRangep->lhsp(), Unbounded)
                                          ? insideRangep->lhsp()->cloneTree(false)
                                          : getFourstateExpressionValue(insideRangep->lhsp());
            AstNodeExpr* const rhsp = VN_IS(insideRangep->rhsp(), Unbounded)
                                          ? insideRangep->rhsp()->cloneTree(false)
                                          : getFourstateExpressionValue(insideRangep->rhsp());
            m_resultp = new AstInsideRange{insideRangep->fileline(), lhsp, rhsp};
            m_resultp->dtypep(getTwoStateDtype(insideRangep->dtypep()));
        }

        void visit(AstShiftL* const shiftlp) override {
            m_resultp = newFourstateShift<AstShiftL>(shiftlp, false);
        }
        void visit(AstShiftR* const shiftrp) override {
            m_resultp = newFourstateShift<AstShiftR>(shiftrp, false);
        }
        void visit(AstShiftRS* const shiftrsp) override {
            m_resultp = newFourstateShift<AstShiftRS>(shiftrsp, false);
        }
        void visit(AstExtend* const extendp) override {
            FileLine* const flp = extendp->fileline();
            m_resultp = new AstExtend{flp, getFourstateExpressionValue(extendp->lhsp(), false),
                                      extendp->width()};
        }
        void visit(AstExtendS* const extendsp) override {
            FileLine* const flp = extendsp->fileline();
            m_resultp = new AstExtendS{flp, getFourstateExpressionValue(extendsp->lhsp(), false),
                                       extendsp->width()};
        }

        void visit(AstCReset* const cresetp) override {
            m_resultp = cresetp->cloneTree(false);
            m_resultp->dtypep(getTwoStateDtype(cresetp->dtypep()));
        }
        void visit(AstConst* const constp) override {
            noTmp();
            AstConst* const newp = constp->cloneTree(false);
            newp->num().opBitsOneX(constp->num());
            newp->dtypeSetBitUnsized(newp->width(), newp->dtypep()->widthMin(),
                                     newp->dtypep()->numeric());
            m_resultp = newp;
        }
        void visit(AstNodeFTaskRef* const funcp) override {
            fourstateExpressionFuncRefHandler(funcp);
            noTmp();
            m_resultp = getExprValuep(funcp)->cloneTree(false);
        }
        void visit(AstCond* const condp) override {
            fourstateExpressionCondHandler(condp);
            noTmp();
            m_resultp = getExprValuep(condp)->cloneTree(false);
        }
        void visit(AstLogAnd* const logAndp) override {
            fourstateExpressionLogAndHandler(logAndp);
            noTmp();
            m_resultp = getExprValuep(logAndp)->cloneTree(false);
        }
        void visit(AstLogOr* const logOrp) override {
            fourstateExpressionLogOrHandler(logOrp);
            noTmp();
            m_resultp = getExprValuep(logOrp)->cloneTree(false);
        }
        void visit(AstSel* const selp) override {
            m_resultp = m_fourstateVisitor.getFourstateExpressionSelHandler(
                selp, getFourstateExpressionValue(selp->fromp(), false), false);
        }

        void visit(AstArraySel* const arraySelp) override {
            m_resultp = m_fourstateVisitor.getFourstateExpressionArraySelHandler(arraySelp, false);
        }

        void visit(AstSliceSel* const sliceSelp) override {
            m_resultp = new AstSliceSel{sliceSelp->fileline(),
                                        getFourstateExpressionValue(sliceSelp->fromp()),
                                        sliceSelp->declRange()};
            m_resultp->dtypep(getTwoStateDtype(sliceSelp->dtypep()));
            setSelpHandled(m_resultp);
        }

        void visit(AstRedAnd* const redAndp) override {
            // &(a.value | a.xz)
            enforceTmp();
            FileLine* const flp = redAndp->fileline();
            m_resultp = new AstRedAnd{
                flp, new AstOr{flp, getFourstateExpressionValue(redAndp->lhsp(), false),
                               getFourstateExpressionXZ(redAndp->lhsp())}};
        }
        void visit(AstRedOr* const redOrp) override {
            // |(a.value | a.xz)
            FileLine* const flp = redOrp->fileline();
            m_resultp
                = new AstRedOr{flp, new AstOr{flp, getFourstateExpressionValue(redOrp->lhsp()),
                                              getFourstateExpressionXZ(redOrp->lhsp())}};
        }
        void visit(AstRedXor* const redXorp) override {
            // |a.xz | ^a.value
            FileLine* const flp = redXorp->fileline();
            m_resultp = new AstOr{
                flp, new AstRedOr{flp, getFourstateExpressionXZ(redXorp->lhsp())},
                new AstRedXor{flp, getFourstateExpressionValue(redXorp->lhsp(), false)}};
        }

        template <typename Operator_T>
        void getFourstateExpressionArithmeticValue(Operator_T* const biop) {
            // |(a.xz | b.xz) ? '1 : (a op b)
            FileLine* const flp = biop->fileline();
            m_resultp = new AstCond{
                flp,
                new AstRedOr{flp, new AstOr{flp, getFourstateExpressionXZ(biop->lhsp()),
                                            getFourstateExpressionXZ(biop->rhsp())}},
                createZeroOrOnesp(biop, true),
                new Operator_T{
                    flp,
                    getFourstateExpressionValue(
                        biop->lhsp(), true /*must be in tmp so it always gets evaluated*/),
                    getFourstateExpressionValue(
                        biop->rhsp(), true /*must be in tmp so it always gets evaluated*/)}};
        }
        void visit(AstAdd* const addp) override { getFourstateExpressionArithmeticValue(addp); }
        void visit(AstSub* const subp) override { getFourstateExpressionArithmeticValue(subp); }
        void visit(AstMul* const mulp) override { getFourstateExpressionArithmeticValue(mulp); }
        void visit(AstMulS* const mulsp) override { getFourstateExpressionArithmeticValue(mulsp); }

        template <typename Operator_T>
        void getFourstateExpressionDivValue(Operator_T* const biop) {
            // |(a.xz | b.xz) | ~|b.value ? '1 : (a op b)
            FileLine* const flp = biop->fileline();
            Operator_T* const resultp = new Operator_T{
                flp,
                getFourstateExpressionValue(biop->lhsp(),
                                            true /*must be in tmp so it always gets evaluated*/),
                getFourstateExpressionValue(biop->rhsp(),
                                            true /*must be in tmp so it always gets evaluated*/)};
            setTwostate(resultp);
            m_resultp = new AstCond{
                flp,
                new AstOr{
                    flp,
                    new AstRedOr{flp, new AstOr{flp, getFourstateExpressionXZ(biop->lhsp()),
                                                getFourstateExpressionXZ(biop->rhsp())}},
                    new AstNot{flp, new AstRedOr{flp, getFourstateExpressionValue(biop->rhsp())}}},
                createZeroOrOnesp(biop, true), resultp};
        }
        void visit(AstDiv* const divp) override { getFourstateExpressionDivValue(divp); }
        void visit(AstDivS* const divsp) override { getFourstateExpressionDivValue(divsp); }
        void visit(AstModDiv* const moddivp) override { getFourstateExpressionDivValue(moddivp); }
        void visit(AstModDivS* const moddivsp) override {
            getFourstateExpressionDivValue(moddivsp);
        }

        void visit(AstConcat* const concatp) override {
            // {a.value, b.value}
            m_resultp = new AstConcat{concatp->fileline(),
                                      getFourstateExpressionValue(concatp->lhsp(), false),
                                      getFourstateExpressionValue(concatp->rhsp(), false)};
        }
        void visit(AstReplicate* const replicatep) override {
            // {count{src.value}}
            // IEEE 1800-2023 11.4.12.1 Replication operator:
            // 'A replication operator (also called a multiple concatenation) is expressed by a
            // concatenation preceded by a non-negative, non-x, and non-z constant expression,
            // called a multiplier'...
            // Because of that `replicatep->countp()` is just cloned
            m_resultp = new AstReplicate{replicatep->fileline(),
                                         getFourstateExpressionValue(replicatep->srcp(), false),
                                         replicatep->countp()->cloneTree(false)};
            m_resultp->dtypeSetBitUnsized(replicatep->width(), replicatep->dtypep()->widthMin(),
                                          replicatep->dtypep()->numeric());
        }
        void visit(AstCastWrap* const castWrapp) override {
            // Cast to anything to fourstate
            m_resultp = getFourstateExpressionValue(castWrapp->lhsp(), false);
        }

        void visit(AstStreamL* const streamlp) override {
            m_resultp = new AstStreamL{streamlp->fileline(),
                                       getFourstateExpressionValue(streamlp->lhsp(), false),
                                       streamlp->rhsp()->cloneTree(false)};
            m_resultp->dtypep(getTwoStateDtype(streamlp->dtypep()));
        }

        void visit(AstStreamR* const streamrp) override {
            m_resultp = new AstStreamR{streamrp->fileline(),
                                       getFourstateExpressionValue(streamrp->lhsp(), false),
                                       streamrp->rhsp()->cloneTree(false)};
            m_resultp->dtypep(getTwoStateDtype(streamrp->dtypep()));
        }

        void visit(AstMemberSel* const memberSelp) override {
            m_fourstateVisitor.splitVar(memberSelp->varp());
            AstMemberSel* const newp = new AstMemberSel{
                memberSelp->fileline(), m_fourstateVisitor.getMemberReceiver(memberSelp),
                getSplittedValue(memberSelp->varp())};
            newp->name(memberSelp->name() + FOURSTATE_VALUE_SUFFIX);
            newp->access(memberSelp->access());
            m_resultp = newp;
        }

        // void visit(AstStructSel* const structSelp) override {
        //     // This may potentially be called twice - for value and xz.
        //     // To fix it it simple need to be added to precalculations
        //     structSelp->fromp()->purityCheck();
        //     m_resultp
        //         = new AstStructSel{structSelp->fileline(),
        //         structSelp->fromp()->cloneTree(false),
        //                            structSelp->name() + FOURSTATE_VALUE_SUFFIX};
        // }

        void visit(AstNodeVarRef* const varRefp) override {
            noTmp();
            if (needsSplitting(varRefp->varp()->dtypep())) {
                m_fourstateVisitor.splitVar(varRefp->varp());
                AstNodeVarRef* const newp = varRefp->cloneTree(false);
                if (!newp->name().empty()) newp->name(newp->name() + FOURSTATE_VALUE_SUFFIX);
                newp->varp(getSplittedValue(varRefp->varp()));
                newp->dtypep(getTwoStateDtype(varRefp->varp()->dtypep()));
                m_resultp = newp;
            } else {
                AstNodeVarRef* const newp = varRefp->cloneTree(false);
                varRefp->dtypep(getTwoStateDtype(varRefp->varp()->dtypep()));
                m_resultp = newp;
            }
        }

        void visit(AstCMethodHard* const cMethodHardp) override {
            fourstateExpressionCMethodHardHandler(cMethodHardp);
            m_resultp = getExprValuep(cMethodHardp);
        }

        void visit(AstSampled* const sampledp) override {
            m_resultp = new AstSampled{
                sampledp->fileline(),
                getFourstateExpressionValue(VN_AS(sampledp->exprp(), NodeExpr), false),
                getTwoStateDtype(sampledp->dtypep()), sampledp->internal()};
        }

        void visit(AstExprStmt* exprStmtp) override {
            fourstateExpressionExprStmtHandler(exprStmtp);
            m_resultp = getExprValuep(exprStmtp)->cloneTree(false);
        }
        void visit(AstNodeExpr* const exprp) override {
            exprp->v3warn(E_UNSUPPORTED,
                          "Unsupported: Operator: " << exprp->typeName() << " with --fourstate");
            // Workaround to avoid Internal errors
            m_resultp = new AstConst{exprp->fileline(), AstConst::BitFalse{}};
        }
        void visit(AstNode* const nodep) override {  // LCOV_EXCL_LINE
            nodep->v3fatalSrc("This node shall be unreachable in this visitor");
        }

        AstNodeExpr* getCache(const AstNodeExpr* const keyp) override {
            return getExprValuep(keyp);
        }
        void setCache(AstNodeExpr* keyp, AstNodeExpr* const valuep) override {
            setExprValuep(keyp, valuep);
        }

    public:
        using FourstateExpressionVisitor::FourstateExpressionVisitor;
        ~FourstateExpressionValueVisitor() override = default;

        AstNodeExpr* getFourstateExpressionValue(AstNodeExpr* const exprp,
                                                 bool putIntoTmp = true) override {
            if (!isFourstate(exprp)) {
                AstStmtExpr* const holderp
                    = new AstStmtExpr{exprp->fileline(), exprp->cloneTree(false)};
                m_fourstateVisitor.iterateChildren(holderp);
                AstNodeExpr* const resultp = holderp->exprp()->unlinkFrBack();
                holderp->deleteTree();
                return resultp;
            }
            return get(exprp, putIntoTmp);
        }
    };

    // Visitor used to get an expression with a value of an xz part of a four-state expression
    // This can be thought as a function - but a Visitor was used to be able to use vtable, create
    // some enclosing namespace and benefit from inheritance
    class FourstateExpressionXZVisitor final : public FourstateExpressionVisitor {

        void visit(AstAnd* const andp) override {
            // (a.value & b.xz) | (b.value & a.xz) | (a.xz & b.xz)
            FileLine* const flp = andp->fileline();
            m_resultp
                = new AstOr{flp,
                            new AstOr{flp,
                                      new AstAnd{flp, getFourstateExpressionValue(andp->lhsp()),
                                                 getFourstateExpressionXZ(andp->rhsp())},
                                      new AstAnd{flp, getFourstateExpressionValue(andp->rhsp()),
                                                 getFourstateExpressionXZ(andp->lhsp())}},
                            new AstAnd{flp, getFourstateExpressionXZ(andp->lhsp()),
                                       getFourstateExpressionXZ(andp->rhsp())}};
        }
        void visit(AstOr* const orp) override {
            // (a.xz & b.xz) | (a.xz & ~b.value) | (b.xz & ~a.value)
            FileLine* const flp = orp->fileline();
            m_resultp = new AstOr{
                flp,
                new AstOr{flp,
                          new AstAnd{flp, getFourstateExpressionXZ(orp->lhsp()),
                                     getFourstateExpressionXZ(orp->rhsp())},
                          new AstAnd{flp, getFourstateExpressionXZ(orp->lhsp()),
                                     new AstNot{flp, getFourstateExpressionValue(orp->rhsp())}}},
                new AstAnd{flp, getFourstateExpressionXZ(orp->rhsp()),
                           new AstNot{flp, getFourstateExpressionValue(orp->lhsp())}}};
        }
        void visit(AstXor* const xorp) override {
            // a.xz | b.xz
            FileLine* const flp = xorp->fileline();
            m_resultp = new AstOr{flp, getFourstateExpressionXZ(xorp->lhsp()),
                                  getFourstateExpressionXZ(xorp->rhsp())};
        }
        void visit(AstNot* const notp) override {
            // a.xz
            m_resultp = getFourstateExpressionXZ(notp->lhsp());
        }

        void visitCompare(AstNodeBiop* const cmpp) {
            // |(a.xz | b.xz)
            enforceTmp();
            FileLine* const flp = cmpp->fileline();
            m_resultp = new AstRedOr{flp, new AstOr{flp, getFourstateExpressionXZ(cmpp->lhsp()),
                                                    getFourstateExpressionXZ(cmpp->rhsp())}};
        }
        void visit(AstEq* const eqp) override { visitCompare(eqp); }
        void visit(AstNeq* const neqp) override { visitCompare(neqp); }
        void visit(AstGt* const gtp) override { visitCompare(gtp); }
        void visit(AstGte* const gtep) override { visitCompare(gtep); }
        void visit(AstLt* const ltp) override { visitCompare(ltp); }
        void visit(AstLte* const ltep) override { visitCompare(ltep); }
        void visit(AstGtS* const gtp) override { visitCompare(gtp); }
        void visit(AstGteS* const gtep) override { visitCompare(gtep); }
        void visit(AstLtS* const ltp) override { visitCompare(ltp); }
        void visit(AstLteS* const ltep) override { visitCompare(ltep); }

        void visit(AstEqWild* const eqWildp) override {
            // |(a.xz & ~b.xz)
            enforceTmp();
            FileLine* const flp = eqWildp->fileline();
            m_resultp = new AstRedOr{
                flp, new AstAnd{flp, getFourstateExpressionXZ(eqWildp->lhsp(), false),
                                new AstNot{flp, getFourstateExpressionXZ(eqWildp->rhsp())}}};
        }
        void visit(AstNeqWild* const neqWildp) override {
            // |(a.xz & ~b.xz)
            enforceTmp();
            FileLine* const flp = neqWildp->fileline();
            m_resultp = new AstRedOr{
                flp, new AstAnd{flp, getFourstateExpressionXZ(neqWildp->lhsp(), false),
                                new AstNot{flp, getFourstateExpressionXZ(neqWildp->rhsp())}}};
        }

        void visit(AstInsideRange* const insideRangep) override {
            AstNodeExpr* const lhsp = VN_IS(insideRangep->lhsp(), Unbounded)
                                          ? insideRangep->lhsp()->cloneTree(false)
                                          : getFourstateExpressionXZ(insideRangep->lhsp());
            AstNodeExpr* const rhsp = VN_IS(insideRangep->rhsp(), Unbounded)
                                          ? insideRangep->rhsp()->cloneTree(false)
                                          : getFourstateExpressionXZ(insideRangep->rhsp());
            m_resultp = new AstInsideRange{insideRangep->fileline(), lhsp, rhsp};
            m_resultp->dtypep(getTwoStateDtype(insideRangep->dtypep()));
        }

        void visit(AstShiftL* const shiftlp) override {
            m_resultp = newFourstateShift<AstShiftL>(shiftlp, true);
        }
        void visit(AstShiftR* const shiftrp) override {
            m_resultp = newFourstateShift<AstShiftR>(shiftrp, true);
        }
        void visit(AstShiftRS* const shiftrsp) override {
            m_resultp = newFourstateShift<AstShiftRS>(shiftrsp, true);
        }
        void visit(AstExtend* const extendp) override {
            FileLine* const flp = extendp->fileline();
            m_resultp = new AstExtend{flp, getFourstateExpressionXZ(extendp->lhsp(), false),
                                      extendp->width()};
        }
        void visit(AstExtendS* const extendsp) override {
            FileLine* const flp = extendsp->fileline();
            m_resultp = new AstExtendS{flp, getFourstateExpressionXZ(extendsp->lhsp(), false),
                                       extendsp->width()};
        }

        void visit(AstCReset* const cresetp) override {
            m_resultp = cresetp->cloneTree(false);
            m_resultp->dtypep(getTwoStateDtype(cresetp->dtypep()));
        }
        void visit(AstConst* const constp) override {
            noTmp();
            AstConst* const newp = constp->cloneTree(false);
            newp->num().opBitsXZ(constp->num());
            newp->dtypeSetBitSized(newp->width(), newp->dtypep()->numeric());
            m_resultp = newp;
        }
        void visit(AstRedAnd* const redAndp) override {
            // &(a.value | a.xz) & |a.xz
            FileLine* const flp = redAndp->fileline();
            m_resultp = new AstAnd{flp, getFourstateExpressionValue(redAndp),
                                   new AstRedOr{flp, getFourstateExpressionXZ(redAndp->lhsp())}};
        }
        void visit(AstRedOr* const redOrp) override {
            // |a.xz & ~|(a.value & ~a.xz)
            FileLine* const flp = redOrp->fileline();
            m_resultp = new AstAnd{
                flp, new AstRedOr{flp, getFourstateExpressionXZ(redOrp->lhsp())},
                new AstNot{
                    flp,
                    new AstRedOr{flp, new AstAnd{flp, getFourstateExpressionValue(redOrp->lhsp()),
                                                 new AstNot{flp, getFourstateExpressionXZ(
                                                                     redOrp->lhsp())}}}}};
        }
        void visit(AstRedXor* const redXorp) override {
            // |a.xz
            m_resultp
                = new AstRedOr{redXorp->fileline(), getFourstateExpressionXZ(redXorp->lhsp())};
        }

        void getFourstateExpressionArithmeticXZ(AstNodeBiop* const biop) {
            // |(a.xz | b.xz) ? '1 : '0
            FileLine* const flp = biop->fileline();
            m_resultp = new AstCond{
                flp,
                new AstRedOr{flp, new AstOr{flp, getFourstateExpressionXZ(biop->lhsp()),
                                            getFourstateExpressionXZ(biop->rhsp())}},
                createZeroOrOnesp(biop, true), createZeroOrOnesp(biop)};
        }
        void visit(AstAdd* const addp) override { getFourstateExpressionArithmeticXZ(addp); }
        void visit(AstSub* const subp) override { getFourstateExpressionArithmeticXZ(subp); }
        void visit(AstMul* const mulp) override { getFourstateExpressionArithmeticXZ(mulp); }
        void visit(AstMulS* const mulsp) override { getFourstateExpressionArithmeticXZ(mulsp); }

        void getFourstateExpressionDivValue(AstNodeBiop* const biop) {
            // |(a.xz | b.xz) | ~|b.value ? '1 : '0
            FileLine* const flp = biop->fileline();
            m_resultp = new AstCond{
                flp,
                new AstOr{
                    flp,
                    new AstRedOr{flp, new AstOr{flp, getFourstateExpressionXZ(biop->lhsp()),
                                                getFourstateExpressionXZ(biop->rhsp())}},
                    new AstNot{flp, new AstRedOr{flp, getFourstateExpressionValue(biop->rhsp())}}},
                createZeroOrOnesp(biop, true), createZeroOrOnesp(biop, false)};
        }
        void visit(AstDiv* const divp) override { getFourstateExpressionDivValue(divp); }
        void visit(AstDivS* const divsp) override { getFourstateExpressionDivValue(divsp); }
        void visit(AstModDiv* const moddivp) override { getFourstateExpressionDivValue(moddivp); }
        void visit(AstModDivS* const moddivsp) override {
            getFourstateExpressionDivValue(moddivsp);
        }

        void visit(AstConcat* const concatp) override {
            // {a.xz, b.xz}
            m_resultp = new AstConcat{concatp->fileline(),
                                      getFourstateExpressionXZ(concatp->lhsp(), false),
                                      getFourstateExpressionXZ(concatp->rhsp(), false)};
        }
        void visit(AstReplicate* const replicatep) override {
            // {count{src.value}}
            // IEEE 1800-2023 11.4.12.1 Replication operator:
            // 'A replication operator (also called a multiple concatenation) is expressed by a
            // concatenation preceded by a non-negative, non-x, and non-z constant expression,
            // called a multiplier'...
            // Because of that `replicatep->countp()` is just cloned
            m_resultp = new AstReplicate{replicatep->fileline(),
                                         getFourstateExpressionXZ(replicatep->srcp(), false),
                                         replicatep->countp()->cloneTree(false)};
            m_resultp->dtypeSetBitUnsized(replicatep->width(), replicatep->dtypep()->widthMin(),
                                          replicatep->dtypep()->numeric());
        }
        void visit(AstCastWrap* const castWrapp) override {
            // Cast to anything to fourstate
            m_resultp = getFourstateExpressionXZ(castWrapp->lhsp(), false);
        }

        void visit(AstStreamL* const streamlp) override {
            m_resultp = new AstStreamL{streamlp->fileline(),
                                       getFourstateExpressionXZ(streamlp->lhsp(), false),
                                       streamlp->rhsp()->cloneTree(false)};
            m_resultp->dtypep(getTwoStateDtype(streamlp->dtypep()));
        }

        void visit(AstStreamR* const streamrp) override {
            m_resultp = new AstStreamR{streamrp->fileline(),
                                       getFourstateExpressionXZ(streamrp->lhsp(), false),
                                       streamrp->rhsp()->cloneTree(false)};
            m_resultp->dtypep(getTwoStateDtype(streamrp->dtypep()));
        }

        void visit(AstMemberSel* const memberSelp) override {
            m_fourstateVisitor.splitVar(memberSelp->varp());
            AstMemberSel* const newp = new AstMemberSel{
                memberSelp->fileline(), m_fourstateVisitor.getMemberReceiver(memberSelp),
                getSplittedXZ(memberSelp->varp())};
            newp->name(memberSelp->name() + FOURSTATE_XZ_SUFFIX);
            newp->access(memberSelp->access());
            m_resultp = newp;
        }

        // void visit(AstStructSel* const structSelp) override {
        //     // This may potentially be called twice - for value and xz.
        //     // To fix it it simple need to be added to precalculations
        //     structSelp->fromp()->purityCheck();
        //     m_resultp
        //         = new AstStructSel{structSelp->fileline(),
        //         structSelp->fromp()->cloneTree(false),
        //                            structSelp->name() + FOURSTATE_XZ_SUFFIX};
        // }

        void visit(AstNodeFTaskRef* const funcp) override {
            fourstateExpressionFuncRefHandler(funcp);
            noTmp();
            m_resultp = getExprXZp(funcp)->cloneTree(false);
        }
        void visit(AstCond* const condp) override {
            fourstateExpressionCondHandler(condp);
            noTmp();
            m_resultp = getExprXZp(condp)->cloneTree(false);
        }
        void visit(AstLogAnd* const logAndp) override {
            fourstateExpressionLogAndHandler(logAndp);
            noTmp();
            m_resultp = getExprXZp(logAndp)->cloneTree(false);
        }
        void visit(AstLogOr* const logOrp) override {
            fourstateExpressionLogOrHandler(logOrp);
            noTmp();
            m_resultp = getExprXZp(logOrp)->cloneTree(false);
        }
        void visit(AstSel* const selp) override {
            m_resultp = m_fourstateVisitor.getFourstateExpressionSelHandler(
                selp, getFourstateExpressionXZ(selp->fromp(), false), false);
        }

        void visit(AstArraySel* const arraySelp) override {
            m_resultp = m_fourstateVisitor.getFourstateExpressionArraySelHandler(arraySelp, true);
        }

        void visit(AstSliceSel* const sliceSelp) override {
            m_resultp = new AstSliceSel{sliceSelp->fileline(),
                                        getFourstateExpressionXZ(sliceSelp->fromp()),
                                        sliceSelp->declRange()};
            m_resultp->dtypep(getTwoStateDtype(sliceSelp->dtypep()));
            setSelpHandled(m_resultp);
        }

        void visit(AstNodeVarRef* const varRefp) override {
            noTmp();
            if (needsSplitting(varRefp->varp()->dtypep())) {
                m_fourstateVisitor.splitVar(varRefp->varp());
                AstNodeVarRef* const newp = varRefp->cloneTree(false);
                if (!newp->name().empty()) newp->name(newp->name() + FOURSTATE_XZ_SUFFIX);
                newp->varp(getSplittedXZ(varRefp->varp()));
                newp->dtypep(getTwoStateDtype(varRefp->varp()->dtypep()));
                m_resultp = newp;
            } else {
                AstConst* const newp = new AstConst{varRefp->fileline(), AstConst::WidthedValue{},
                                                    varRefp->width(), 0};
                m_resultp = newp;
            }
        }

        void visit(AstCMethodHard* const cMethodHardp) override {
            fourstateExpressionCMethodHardHandler(cMethodHardp);
            m_resultp = getExprXZp(cMethodHardp);
        }

        void visit(AstSampled* const sampledp) override {
            m_resultp = new AstSampled{
                sampledp->fileline(),
                getFourstateExpressionXZ(VN_AS(sampledp->exprp(), NodeExpr), false),
                getTwoStateDtype(sampledp->dtypep()), sampledp->internal()};
        }

        void visit(AstLogNot* const logNotp) override {
            FileLine* const flp = logNotp->fileline();
            AstNodeExpr* const knownOnep
                = new AstRedOr{flp, m_fourstateVisitor.getTwoStateCast(logNotp->lhsp())};
            m_resultp
                = new AstLogAnd{flp, new AstRedOr{flp, getFourstateExpressionXZ(logNotp->lhsp())},
                                new AstLogNot{flp, knownOnep}};
        }

        void visit(AstOneHot* const nodep) override {
            m_resultp = new AstConst{nodep->fileline(), AstConst::BitFalse{}};
        }

        void visit(AstOneHot0* const nodep) override {
            m_resultp = new AstConst{nodep->fileline(), AstConst::BitFalse{}};
        }

        void visit(AstCountBits* const nodep) override {
            m_resultp
                = new AstConst{nodep->fileline(), AstConst::WidthedValue{}, nodep->width(), 0U};
        }

        void visit(AstCLog2* const nodep) override {
            FileLine* const flp = nodep->fileline();
            m_resultp
                = new AstCond{flp, new AstRedOr{flp, getFourstateExpressionXZ(nodep->lhsp())},
                              createZeroOrOnesp(nodep, true), createZeroOrOnesp(nodep)};
        }

        void visit(AstExprStmt* exprStmtp) override {
            fourstateExpressionExprStmtHandler(exprStmtp);
            m_resultp = getExprXZp(exprStmtp)->cloneTree(false);
        }
        void visit(AstNodeExpr* const exprp) override {
            exprp->v3warn(E_UNSUPPORTED,
                          "Unsupported: Operator: " << exprp->typeName() << " with --fourstate");
            // Workaround to avoid Internal errors
            m_resultp = new AstConst{exprp->fileline(), AstConst::BitFalse{}};
        }
        void visit(AstNode* const nodep) override {  // LCOV_EXCL_LINE
            nodep->v3fatalSrc("This node shall be unreachable in this visitor");
        }

        AstNodeExpr* getCache(const AstNodeExpr* const keyp) override { return getExprXZp(keyp); }
        void setCache(AstNodeExpr* keyp, AstNodeExpr* const valuep) override {
            setExprXZp(keyp, valuep);
        }

    public:
        using FourstateExpressionVisitor::FourstateExpressionVisitor;
        ~FourstateExpressionXZVisitor() override = default;

        AstNodeExpr* getFourstateExpressionXZ(AstNodeExpr* const exprp,
                                              bool putIntoTmp = true) override {
            if (!isFourstate(exprp)) return createZeroOrOnesp(exprp);
            return get(exprp, putIntoTmp);
        }
    };

    FourstateExpressionValueVisitor
        m_fourstateGeneratorValueVisitor;  // Generator of four-state expressions (value part)
    FourstateExpressionXZVisitor
        m_fourstateGeneratorXZVisitor;  // Generator of four-state expressions (xz part)

    AstNodeExpr* getFourstateExpressionValue(AstNodeExpr* const exprp, bool putIntoTmp = false) {
        if (AstCReset* const cresetp = VN_CAST(exprp, CReset)) {
            // This is here instead in the visitor because CReset shall never be nested into
            // the expression and also it is a very special case
            AstCReset* const resultp = cresetp->cloneTree(false);
            resultp->dtypep(getTwoStateDtype(cresetp->dtypep()));
            FourstateLogicTypePropagator{resultp};
            return resultp;
        }
        AstNodeExpr* const result
            = m_fourstateGeneratorValueVisitor.getFourstateExpressionValue(exprp, putIntoTmp);
        FourstateLogicTypePropagator{result};
        return result;
    }
    AstNodeExpr* getFourstateExpressionXZ(AstNodeExpr* const exprp, bool putIntoTmp = false) {
        if (AstCReset* const cresetp = VN_CAST(exprp, CReset)) {
            // This is here instead in the visitor because CReset shall never be nested into
            // the expression and also it is a very special case
            AstCReset* const resultp = cresetp->cloneTree(false);
            resultp->dtypep(getTwoStateDtype(cresetp->dtypep()));
            FourstateLogicTypePropagator{resultp};
            return resultp;
        }
        AstNodeExpr* const result
            = m_fourstateGeneratorXZVisitor.getFourstateExpressionXZ(exprp, putIntoTmp);
        FourstateLogicTypePropagator{result};
        return result;
    }
    AstNodeExpr* getTruthExpr(AstNodeExpr* const exprp) {
        UASSERT_OBJ(isFourstate(exprp), exprp,
                    "This function is ment to be called on four-state expressions");
        // a.value && !a.xz
        FileLine* const flp = exprp->fileline();
        AstLogAnd* const result
            = new AstLogAnd{flp, getFourstateExpressionValue(exprp),
                            new AstLogNot{flp, getFourstateExpressionXZ(exprp)}};
        setFourstate(result, false);
        setFourstate(result->rhsp(), false);
        return result;
    }
    AstNodeExpr* getTwoStateCast(AstNodeExpr* const exprp) {
        UASSERT_OBJ(isFourstate(exprp), exprp,
                    "This function is ment to be called on four-state expressions");
        return getTwoStateCast(getFourstateExpressionValue(exprp),
                               getFourstateExpressionXZ(exprp));
    }

    AstNodeExpr* getTwoStateCast(AstNodeExpr* const exprValuep, AstNodeExpr* const exprXZp) {
        // (a.value & (~a.xz))
        FileLine* const flp = exprValuep->fileline();
        AstAnd* const result = new AstAnd{flp, exprValuep, new AstNot{flp, exprXZp}};
        setFourstate(result, false);
        setFourstate(result->rhsp(), false);
        return result;
    }

    AstNodeExpr* getCoverTogglePart(AstNodeExpr* const exprp, const bool xzPart) {
        // Toggle indices are generated in bounds. Keep this declarative coverage tree free of
        // procedural index snapshots, which cannot be inserted beside an AstCoverToggle.
        if (VN_IS(exprp, Const)) {
            if (isFourstate(exprp)) {
                return xzPart ? getFourstateExpressionXZ(exprp)
                              : getFourstateExpressionValue(exprp);
            }
            return xzPart ? createZeroOrOnesp(exprp) : exprp->cloneTree(false);
        } else if (AstNodeVarRef* const varRefp = VN_CAST(exprp, NodeVarRef)) {
            if (needsSplitting(varRefp->varp()->dtypep())) splitVar(varRefp->varp());
            if (getValuePartVarp(varRefp->varp())) {
                AstNodeVarRef* const newp = varRefp->cloneTree(false);
                if (xzPart && !newp->name().empty()) {
                    newp->name(newp->name() + FOURSTATE_XZ_SUFFIX);
                }
                newp->varp(xzPart ? getSplittedXZ(varRefp->varp())
                                  : getSplittedValue(varRefp->varp()));
                newp->dtypep(getTwoStateDtype(varRefp->varp()->dtypep()));
                setFourstate(newp, false);
                return newp;
            }
            return xzPart ? createZeroOrOnesp(exprp) : exprp->cloneTree(false);
        } else if (AstArraySel* const arraySelp = VN_CAST(exprp, ArraySel)) {
            UASSERT_OBJ(VN_IS(arraySelp->bitp(), Const), arraySelp,
                        "Toggle coverage array index must be constant");
            AstArraySel* const newp = new AstArraySel{
                arraySelp->fileline(), getCoverTogglePart(arraySelp->fromp(), xzPart),
                isFourstate(arraySelp->bitp()) ? getTwoStateCast(arraySelp->bitp())
                                               : arraySelp->bitp()->cloneTree(false)};
            newp->dtypep(getTwoStateDtype(arraySelp->dtypep()));
            setFourstate(newp, false);
            setSelpHandled(newp);
            return newp;
        } else if (AstSel* const selp = VN_CAST(exprp, Sel)) {
            UASSERT_OBJ(VN_IS(selp->lsbp(), Const), selp,
                        "Toggle coverage packed index must be constant");
            AstSel* const newp = selp->cloneTree(false);
            newp->fromp(getCoverTogglePart(selp->fromp(), xzPart));
            newp->lsbp(selp->lsbp()->cloneTree(false));
            newp->dtypep(getTwoStateDtype(selp->dtypep()));
            setFourstate(newp, false);
            setSelpHandled(newp);
            return newp;
        }
        exprp->v3fatalSrc("Unable to build toggle coverage selection");
        return nullptr;
    }

    void visit(AstNodeAssign* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (AstDelay* const delayp = VN_CAST(nodep->timingControlp(), Delay)) {
            if (VN_IS(nodep, AssignW)
                && (!delayp->lhsp()->isPure()
                    || (delayp->fallDelay() && !delayp->fallDelay()->isPure()))) {
                delayp->v3warn(E_UNSUPPORTED,
                               "Unsupported: Impure net delay expression with --fourstate");
                pushDeletep(delayp->unlinkFrBack());
            } else {
                if (VN_IS(nodep, Assign) && isFourstate(nodep->lhsp())) {
                    nodep->v3warn(E_UNSUPPORTED,
                                  "Unsupported: Blocking intra-assignment delay with --fourstate");
                }
                // Both split assignments must use the same captured delay. Lower
                // it before cloning, with calculations owned by the assignment.
                lowerFourstateDelay(delayp);
            }
        }
        if (isFourstate(nodep->lhsp())) {
            const auto pullIt = m_pullAssignments.find(nodep);
            const bool hasPull = pullIt != m_pullAssignments.end();
            const FourstatePair pulled = hasPull ? applyImplicitPull(nodep->rhsp(), pullIt->second)
                                                 : FourstatePair{nullptr, nullptr};
            if (hasPull) ++m_statPullFallbacks;
            AstNodeExpr* lhsp = nodep->lhsp()->unlinkFrBack();
            pushDeletep(lhsp);
            AstNodeAssign* const assignXZp = nodep->cloneTree(false);
            {
                assignXZp->rhsp()->unlinkFrBack()->deleteTree();
                AstNodeExpr* const newLhsp = getFourstateExpressionXZ(lhsp);
                assignXZp->lhsp(newLhsp);
                assignXZp->rhsp(hasPull ? pulled.xzp : getFourstateExpressionXZ(nodep->rhsp()));
                assignXZp->dtypeFrom(newLhsp);
                addNextCalculation(assignXZp);
            }
            {
                AstNodeExpr* const newRhsp
                    = hasPull ? pulled.valuep : getFourstateExpressionValue(nodep->rhsp());
                AstNodeExpr* const newLhsp = getFourstateExpressionValue(lhsp);
                pushDeletep(nodep->rhsp()->unlinkFrBack());
                nodep->lhsp(newLhsp);
                nodep->rhsp(newRhsp);
                nodep->dtypeFrom(newLhsp);
            }
            // if (AstAssignW* const assignWValuep = VN_CAST(nodep, AssignW)) {
            //     while (lhsp) {
            //         if (const AstSel* const selp = VN_CAST(lhsp, Sel)) {
            //             lhsp = selp->fromp();
            //         } else if (const AstArraySel* const aselp = VN_CAST(lhsp, ArraySel)) {
            //             lhsp = aselp->fromp();
            //         } else if (const AstSliceSel* const sselp = VN_CAST(lhsp, SliceSel)) {
            //             lhsp = sselp->fromp();
            //         } else {
            //             break;
            //         }
            //     }
            //     if (const AstNodeVarRef* const lhsVarRefp = VN_CAST(lhsp, NodeVarRef)) {
            //         assignWConflictResolution(lhsVarRefp->varp(), assignWValuep,
            //                                   VN_AS(assignXZp, AssignW));
            //         if (const AstNode* const timingControlp = assignWValuep->timingControlp()) {
            //             timingControlp->v3warn(
            //                 E_UNSUPPORTED,
            //                 "Continuous assignment delays are unsupported with --fourstate");
            //         }
            //     } else {
            //         nodep->v3warn(E_UNSUPPORTED,
            //                       "Fourstate LHS other than a simple variable or select "
            //                       "reference is not supported with continuous assignment");
            //     }
            // }
        } else if (isFourstate(nodep->rhsp())) {
            AstNodeExpr* const newRhsp = getTwoStateCast(nodep->rhsp());
            pushDeletep(nodep->rhsp()->unlinkFrBack());
            nodep->rhsp(newRhsp);
        }
        iterateChildren(nodep);
    }
    void visit(AstCMethodHard* const nodep) override {
        // Queue insertion coerces an element to the queue's element type. A
        // two-state queue must discard unknown bits without duplicating calls.
        if ((nodep->method() == VCMethod::ARRAY_PUSH_BACK
             || nodep->method() == VCMethod::ARRAY_PUSH_FRONT)
            && !needsSplitting(nodep->fromp()->dtypep())) {
            if (AstNodeExpr* const pinp = nodep->pinsp()) {
                if (isFourstate(pinp)) {
                    AstNodeExpr* const newp = getTwoStateCast(pinp);
                    pinp->replaceWith(newp);
                    pushDeletep(pinp);
                }
            }
        }
        iterateChildren(nodep);
    }
    void visit(AstStmtExpr* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        auto isFourState = [nodep]() -> bool {
            if (AstNodeFTaskRef* const taskRefp = VN_CAST(nodep->exprp(), NodeFTaskRef)) {
                return isFourstate(taskRefp) && !isFTaskRefHandled(taskRefp);
            }
            return isFourstate(nodep->exprp());
        };
        if (isFourState()) {
            AstNodeExpr* const exprp = nodep->exprp()->unlinkFrBack();
            pushDeletep(exprp);
            nodep->exprp(getFourstateExpressionValue(exprp));
            AstNodeExpr* const newXzp = getFourstateExpressionXZ(exprp);
            iterateChildren(newXzp);
            addNextCalculation(new AstStmtExpr{nodep->fileline(), newXzp});
        }
        iterateChildren(nodep);
    }

    void visit(AstCoverToggle* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        const bool origFourstate = isFourstate(nodep->origp());
        const bool changeFourstate = isFourstate(nodep->changep());
        if (origFourstate || changeFourstate) {
            AstNodeExpr* const origp = nodep->origp()->unlinkFrBack();
            AstNodeExpr* const changep = nodep->changep()->unlinkFrBack();
            // Count changes in the value and X/Z halves separately while sharing the original
            // coverpoint bucket.
            AstCoverToggle* const xzp = nodep->cloneTree(false);
            xzp->incp(nodep->incp()->cloneTree(false));
            xzp->origp(origFourstate ? getCoverTogglePart(origp, true) : createZeroOrOnesp(origp));
            xzp->changep(getCoverTogglePart(changep, true));
            nodep->origp(getCoverTogglePart(origp, false));
            nodep->changep(getCoverTogglePart(changep, false));
            nodep->addNextHere(xzp);
            origp->deleteTree();
            changep->deleteTree();
            FourstateLogicTypePropagator{nodep};
            FourstateLogicTypePropagator{xzp};
        }
        iterateChildren(nodep);
    }

    void visit(AstLoopTest* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (isFourstate(nodep->condp())) {
            AstNodeExpr* const condp = nodep->condp()->unlinkFrBack();
            pushDeletep(condp);
            nodep->condp(getTruthExpr(condp));
        }
        iterateChildren(nodep);
    }
    void lowerFourstateDelay(AstDelay* const nodep) {
        if (!nodep->isCycleDelay() && (isFourstate(nodep->lhsp()) || !nodep->lhsp()->isPure())) {
            AstNodeExpr* const delayp = nodep->lhsp()->unlinkFrBack();
            // An X/Z delay is zero, including mixed known and unknown bits.
            // Capture impure expressions once before testing their X/Z mask.
            const bool impure = !delayp->isPure();
            AstNodeExpr* const valuep
                = impure ? getOnceExpressionValue(delayp) : getFourstateExpressionValue(delayp);
            AstNodeExpr* const newp
                = isFourstate(delayp) ? new AstCond{nodep->fileline(),
                                                    new AstRedOr{nodep->fileline(),
                                                                 getFourstateExpressionXZ(delayp)},
                                                    createZeroOrOnesp(delayp), valuep}
                                      : valuep;
            FourstateLogicTypePropagator{newp};
            if (impure) {
                // Consume both function outputs before timing lowering moves
                // the delay into a separate coroutine. Its cross-function read
                // must survive statement-temporary dead-store elimination.
                AstVar* const varp = new AstVar{
                    nodep->fileline(), m_tmpFuncLocal ? VVarType::BLOCKTEMP : VVarType::MODULETEMP,
                    m_tmpNames.get(nodep), getTwoStateDtype(delayp->dtypep())};
                varp->funcLocal(m_tmpFuncLocal);
                varp->noSubst(true);
                m_currentTmpSpotp->addHereThisAsNext(varp);
                addPrecalculation(
                    new AstAssign{nodep->fileline(),
                                  new AstVarRef{nodep->fileline(), varp, VAccess::WRITE}, newp});
                nodep->lhsp(new AstVarRef{nodep->fileline(), varp, VAccess::READ});
                FourstateLogicTypePropagator{nodep->lhsp()};
            } else {
                nodep->lhsp(newp);
            }
            pushDeletep(delayp);
        }
        iterateChildren(nodep);
    }
    void visit(AstDelay* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        lowerFourstateDelay(nodep);
    }
    void visit(AstNodeIf* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (isFourstate(nodep->condp())) {
            AstNodeExpr* const condp = nodep->condp()->unlinkFrBack();
            pushDeletep(condp);
            nodep->condp(getTruthExpr(condp));
        }
        iterateChildren(nodep);
    }

    void visit(AstWait* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (AstNodeExpr* const condp = nodep->condp()) {
            if (isFourstate(condp)) {
                nodep->condp(getTwoStateCast(condp->unlinkFrBack()));
                condp->deleteTree();
            }
        }
        iterateChildren(nodep);
    }

    void lowerConstantWildcardCase(AstCase* const nodep) {
        // The selector and item may both contain wildcards. Compare both encoded
        // halves after masking X/Z for casex, or only Z for casez.
        if (nodep->caseType() != VCaseType::CT_CASEX && nodep->caseType() != VCaseType::CT_CASEZ) {
            return;
        }
        if (!nodep->exprp()->dtypep()->isIntegralOrPacked()) return;
        bool hasWildcard = false;
        for (AstCaseItem* itemp = nodep->itemsp(); itemp;
             itemp = VN_AS(itemp->nextp(), CaseItem)) {
            for (AstNodeExpr* condp = itemp->condsp(); condp;
                 condp = VN_AS(condp->nextp(), NodeExpr)) {
                const AstConst* const constp = VN_CAST(condp, Const);
                if (!constp || constp->num().isOpaque()) return;
                hasWildcard |= constp->num().isAnyXZ();
            }
        }
        if (!hasWildcard) return;
        const bool casez = nodep->caseType() == VCaseType::CT_CASEZ;
        AstNodeExpr* const selectorp = nodep->exprp();
        AstNodeExpr* const valuep = getOnceExpressionValue(selectorp);
        AstNodeExpr* const xzp = getFourstateExpressionXZ(selectorp);
        for (AstCaseItem* itemp = nodep->itemsp(); itemp;
             itemp = VN_AS(itemp->nextp(), CaseItem)) {
            for (AstNodeExpr *condp = itemp->condsp(), *nextp; condp; condp = nextp) {
                nextp = VN_AS(condp->nextp(), NodeExpr);
                FileLine* const flp = condp->fileline();
                AstNodeExpr* const itemValuep = getFourstateExpressionValue(condp);
                AstNodeExpr* const itemXZp = getFourstateExpressionXZ(condp);
                AstNodeExpr* const selectorMaskp
                    = casez ? static_cast<AstNodeExpr*>(
                                  new AstAnd{flp, xzp->cloneTree(false),
                                             new AstNot{flp, valuep->cloneTree(false)}})
                            : xzp->cloneTree(false);
                AstNodeExpr* const itemMaskp
                    = casez ? static_cast<AstNodeExpr*>(
                                  new AstAnd{flp, itemXZp->cloneTree(false),
                                             new AstNot{flp, itemValuep->cloneTree(false)}})
                            : itemXZp->cloneTree(false);
                AstNodeExpr* const maskp = new AstOr{flp, selectorMaskp, itemMaskp};
                AstNodeExpr* const differencep
                    = new AstConcat{flp, new AstXor{flp, valuep->cloneTree(false), itemValuep},
                                    new AstXor{flp, xzp->cloneTree(false), itemXZp}};
                AstNodeExpr* const matchp = new AstLogNot{
                    flp,
                    new AstRedOr{
                        flp, new AstAnd{flp, differencep,
                                        new AstNot{flp, new AstConcat{flp, maskp->cloneTree(false),
                                                                      maskp}}}}};
                FourstateLogicTypePropagator{matchp};
                condp->replaceWith(matchp);
                pushDeletep(condp);
            }
        }
        pushDeletep(valuep);
        pushDeletep(xzp);
        pushDeletep(selectorp->unlinkFrBack());
        nodep->exprp(new AstConst{nodep->fileline(), AstConst::BitTrue{}});
        FourstateLogicTypePropagator{nodep->exprp()};
    }

    void visit(AstCase* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        lowerConstantWildcardCase(nodep);
        VL_RESTORER(m_caseMaskp);
        VL_RESTORER(m_caseType);
        m_caseMaskp = nullptr;
        m_caseType = nodep->caseType();
        FileLine* const flp = nodep->exprp()->fileline();
        if (nodep->caseInside()) {
            for (AstCaseItem* itemp = nodep->itemsp(); itemp;
                 itemp = VN_AS(itemp->nextp(), CaseItem)) {
                for (AstNodeExpr *nextp, *condp = itemp->condsp(); condp; condp = nextp) {
                    nextp = VN_AS(condp->nextp(), NodeExpr);
                    AstNodeExpr* newp = nullptr;
                    if (AstInsideRange* const insideRangep = VN_CAST(condp, InsideRange)) {
                        newp = insideRangep->newAndFromInside(
                            nodep->exprp()->cloneTreePure(false),
                            insideRangep->lhsp()->cloneTreePure(false),
                            insideRangep->rhsp()->cloneTreePure(false));
                    } else {
                        newp = AstEqWild::newTyped(condp->fileline(),
                                                   nodep->exprp()->cloneTreePure(false),
                                                   condp->cloneTreePure(false));
                    }
                    FourstateLogicTypePropagator{newp};
                    if (isFourstate(newp)) {
                        AstNodeExpr* const oldp = newp;
                        newp = getTruthExpr(oldp);
                        oldp->deleteTree();
                    }
                    VNRelinker relinker;
                    condp->unlinkFrBack(&relinker);
                    relinker.relink(newp);
                    condp->deleteTree();
                }
            }
            nodep->exprp()->unlinkFrBack()->deleteTree();
            nodep->exprp(new AstConst{flp, AstConst::BitTrue{}});
            FourstateLogicTypePropagator{nodep->exprp()};
        }
        if (isFourstate(nodep->exprp())) {
            switch (nodep->caseType()) {
            case VCaseType::CT_CASE: {
                AstNodeExpr* const newp
                    = new AstConcat{flp, getFourstateExpressionValue(nodep->exprp()),
                                    getFourstateExpressionXZ(nodep->exprp())};
                nodep->exprp()->unlinkFrBack()->deleteTree();
                nodep->exprp(newp);
                m_caseMaskp = createZeroOrOnesp(newp);
                break;
            }
            case VCaseType::CT_CASEX: {
                AstNodeExpr* const valuep = getFourstateExpressionValue(nodep->exprp(), true);
                AstNodeExpr* const xzp = getFourstateExpressionXZ(nodep->exprp(), true);
                AstNodeExpr* const newp
                    = new AstConcat{flp, new AstOr{flp, valuep, xzp->cloneTree(false)}, xzp};
                m_caseMaskp = new AstConcat{flp, xzp->cloneTree(false), xzp->cloneTree(false)};
                AstVar* const maskTmpVarp = createTmp(m_caseMaskp);
                addPrecalculation(new AstAssign{
                    flp, new AstVarRef{flp, maskTmpVarp, VAccess::WRITE}, m_caseMaskp});
                m_caseMaskp = new AstVarRef{flp, maskTmpVarp, VAccess::READ};
                AstNodeExpr* const oldp = nodep->exprp();
                oldp->replaceWith(newp);
                oldp->deleteTree();
                break;
            }
            case VCaseType::CT_CASEZ: {
                AstNodeExpr* const valuep = getFourstateExpressionValue(nodep->exprp(), true);
                AstNodeExpr* const xzp = getFourstateExpressionXZ(nodep->exprp(), true);
                AstNodeExpr* const newp
                    = new AstConcat{flp, new AstOr{flp, valuep, xzp->cloneTree(false)}, xzp};
                m_caseMaskp
                    = new AstConcat{flp,
                                    new AstAnd{flp, new AstNot{flp, valuep->cloneTree(false)},
                                               xzp->cloneTree(false)},
                                    new AstAnd{flp, new AstNot{flp, valuep->cloneTree(false)},
                                               xzp->cloneTree(false)}};
                AstVar* const maskTmpVarp = createTmp(m_caseMaskp);
                addPrecalculation(new AstAssign{
                    flp, new AstVarRef{flp, maskTmpVarp, VAccess::WRITE}, m_caseMaskp});
                m_caseMaskp = new AstVarRef{flp, maskTmpVarp, VAccess::READ};
                AstNodeExpr* const oldp = nodep->exprp();
                oldp->replaceWith(newp);
                oldp->deleteTree();
                break;
            }
            case VCaseType::CT_CASEINSIDE: break;
            default: nodep->v3warn(E_UNSUPPORTED, "Unsupported: case type"); break;
            }
            FourstateLogicTypePropagator{nodep->exprp()};
        }
        if (!m_caseMaskp) {
            // Hack lets treat every case as four-state - in order to not treat case as fourstate
            // we would have to check if every AstCaseItems condp is not a four-state
            VNRelinker relinker;
            AstNodeExpr* const oldp = nodep->exprp();
            oldp->unlinkFrBack(&relinker);
            AstNodeExpr* const newp = new AstConcat{flp, oldp, createZeroOrOnesp(oldp)};
            relinker.relink(newp);
            FourstateLogicTypePropagator{newp};
            m_caseMaskp = createZeroOrOnesp(newp);
        }
        iterateChildren(nodep);
        VL_DO_DANGLING(m_caseMaskp->deleteTree(), m_caseMaskp);
    }
    void visit(AstCaseItem* const nodep) override {
        for (AstNodeExpr* condp = nodep->condsp(); condp;
             condp = VN_AS(condp->nextp(), NodeExpr)) {
            FileLine* const flp = condp->fileline();
            if (isFourstate(condp)) {
                if (m_caseType != VCaseType::CT_CASE) {
                    condp->v3warn(E_UNSUPPORTED,
                                  "Four-state values in case items are unsupported");
                }
                UASSERT_OBJ(m_caseMaskp, condp, "Fourstate caseItem but case is not four-state");
                AstNodeExpr* newp
                    = new AstOr{flp,
                                new AstConcat{flp, getFourstateExpressionValue(condp),
                                              getFourstateExpressionXZ(condp)},
                                m_caseMaskp->cloneTreePure(false)};
                condp->replaceWith(newp);
                condp->deleteTree();
                condp = newp;
            } else if (m_caseMaskp) {
                VNRelinker relinker;
                condp->unlinkFrBack(&relinker);
                AstNodeExpr* const newp
                    = new AstOr{flp, new AstConcat{flp, condp, createZeroOrOnesp(condp)},
                                m_caseMaskp->cloneTreePure(false)};
                relinker.relink(newp);
                condp = newp;
            } else {
                condp->v3fatalSrc("Right now we want everything to be four-state here");
            }
        }

        for (AstNodeExpr* condp = nodep->condsp(); condp;
             condp = VN_AS(condp->nextp(), NodeExpr)) {
            FourstateLogicTypePropagator{condp};
        }
        iterateChildren(nodep);
    }
    void visit(AstSenItem* const nodep) override {
        if (!VN_IS(nodep->sensp(), FourstateExpr) && isFourstate(nodep->sensp())) {
            AstNodeExpr* const sensp = nodep->sensp()->unlinkFrBack();
            pushDeletep(sensp);
            nodep->sensp(new AstFourstateExpr{nodep->fileline(),
                                              getFourstateExpressionValue(sensp),
                                              getFourstateExpressionXZ(sensp)});
        }
        iterateChildren(nodep);
    }
    AstNodeExpr* newReadMemBound(AstNodeExpr* const exprp) {
        FileLine* const flp = exprp->fileline();
        AstNodeExpr* valuep = getOnceExpressionValue(exprp);
        AstNodeExpr* xzp = getFourstateExpressionXZ(exprp);
        // Keep signed narrow values negative, and validate unknown bits before any writes.
        if (valuep->width() < 64) {
            valuep = exprp->isSigned() ? static_cast<AstNodeExpr*>(new AstExtendS{flp, valuep, 64})
                                       : static_cast<AstNodeExpr*>(new AstExtend{flp, valuep, 64});
        }
        valuep->dtypeSetBitSized(64, exprp->dtypep()->numeric());
        if (xzp->width() < 64) xzp = new AstExtend{flp, xzp, 64};
        return new AstFourstateExpr{flp, newReadMemCapture(valuep), newReadMemCapture(xzp)};
    }
    AstNodeExpr* newReadMemCapture(AstNodeExpr* const exprp) {
        // Filename strings cannot share the integral temporary pool. Capture arguments
        // before the bounds so neither later argument effects nor C++ evaluation order
        // can change the selected filename or its knownness check.
        FileLine* const flp = exprp->fileline();
        AstNodeDType* const dtypep = needsSplitting(exprp->dtypep())
                                         ? getTwoStateDtype(exprp->dtypep())
                                         : exprp->dtypep();
        AstVar* const varp = new AstVar{flp, VVarType::BLOCKTEMP, m_tmpNames.get(exprp), dtypep};
        varp->funcLocal(m_tmpFuncLocal);
        varp->noReset(true);
        varp->noSubst(true);
        m_currentTmpSpotp->addHereThisAsNext(varp);
        addPrecalculation(new AstAssign{flp, new AstVarRef{flp, varp, VAccess::WRITE}, exprp});
        return new AstVarRef{flp, varp, VAccess::READ};
    }
    void visit(AstReadMem* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (!needsSplitting(nodep->memp()->dtypep())) {
            iterateChildren(nodep);
            return;
        }
        const AstNodeVarRef* const refp = VN_CAST(nodep->memp(), NodeVarRef);
        const AstUnpackArrayDType* const arrayp
            = VN_CAST(nodep->memp()->dtypep()->skipRefp(), UnpackArrayDType);
        const AstBasicDType* const elementp
            = arrayp ? VN_CAST(arrayp->subDTypep()->skipRefp(), BasicDType) : nullptr;
        if (!refp || !arrayp || !elementp || !elementp->keyword().isIntNumeric()) {
            nodep->v3warn(E_UNSUPPORTED, "Unsupported: Four-state $readmem requires a whole fixed "
                                         "one-dimensional integral memory.");
            return;
        }
        if (refp->varp()->isFuncLocal() || refp->varp()->lifetime().isAutomatic()
            || refp->varp()->isRef() || refp->varp()->isClassMember() || refp->varp()->isIO()
            || refp->varp()->isForceable()) {
            nodep->v3warn(E_UNSUPPORTED,
                          "Unsupported: Four-state $readmem into automatic, aliased, port or "
                          "forceable memory.");
            return;
        }
        if ((nodep->lsbp() && nodep->lsbp()->width() > 64)
            || (nodep->msbp() && nodep->msbp()->width() > 64)) {
            nodep->v3warn(E_UNSUPPORTED,
                          "Unsupported: Four-state $readmem address wider than 64 bits.");
            return;
        }
        FileLine* const flp = nodep->fileline();
        AstNodeExpr* const oldMemp = nodep->memp();
        AstNodeExpr* const valuep = getFourstateExpressionValue(oldMemp);
        AstNodeExpr* const xzp = getFourstateExpressionXZ(oldMemp);
        oldMemp->replaceWith(new AstReadMemPair{flp, valuep, xzp});
        pushDeletep(oldMemp);
        if (AstCvtPackString* const packp = VN_CAST(nodep->filenamep(), CvtPackString)) {
            AstNodeExpr* const sourcep = packp->lhsp();
            if (isFourstate(sourcep)) {
                AstNodeExpr* const filenameValuep = getOnceExpressionValue(sourcep);
                AstNodeExpr* const knownp
                    = new AstLogNot{flp, new AstRedOr{flp, getFourstateExpressionXZ(sourcep)}};
                sourcep->replaceWith(filenameValuep);
                pushDeletep(sourcep);
                AstNodeExpr* const filenamep = nodep->filenamep()->unlinkFrBack();
                nodep->filenamep(new AstReadMemFile{flp, filenamep, knownp});
            }
        }
        if (AstReadMemFile* const filep = VN_CAST(nodep->filenamep(), ReadMemFile)) {
            filep->filenamep(newReadMemCapture(filep->filenamep()->unlinkFrBack()));
            filep->knownp(newReadMemCapture(filep->knownp()->unlinkFrBack()));
        } else if (!VN_IS(nodep->filenamep(), Const)) {
            nodep->filenamep(newReadMemCapture(nodep->filenamep()->unlinkFrBack()));
        }
        if (AstNodeExpr* const boundp = nodep->lsbp()) {
            boundp->replaceWith(newReadMemBound(boundp));
            pushDeletep(boundp);
        }
        if (AstNodeExpr* const boundp = nodep->msbp()) {
            boundp->replaceWith(newReadMemBound(boundp));
            pushDeletep(boundp);
        }
        iterateChildren(nodep);
    }
    void visit(AstDisplay* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (nodep->filep() && isFourstate(nodep->filep())) {
            castFourstateWarn(nodep->filep());
            AstNodeExpr* const newp = getTwoStateCast(nodep->filep());
            pushDeletep(nodep->filep()->unlinkFrBack());
            nodep->filep(newp);
        }
        iterateChildren(nodep);
    }
    void visit(AstFClose* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (isFourstate(nodep->filep())) {
            castFourstateWarn(nodep->filep());
            AstNodeExpr* const newp = getTwoStateCast(nodep->filep());
            pushDeletep(nodep->filep()->unlinkFrBack());
            nodep->filep(newp);
        }
        iterateChildren(nodep);
    }
    void visit(AstFFlush* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        if (nodep->filep() && isFourstate(nodep->filep())) {
            castFourstateWarn(nodep->filep());
            AstNodeExpr* const newp = getTwoStateCast(nodep->filep());
            pushDeletep(nodep->filep()->unlinkFrBack());
            nodep->filep(newp);
        }
        iterateChildren(nodep);
    }

    void cArgsHandler(AstNode* nodep) {
        for (; nodep; nodep = nodep->nextp()) {
            if (AstNodeExpr* const exprp = VN_CAST(nodep, NodeExpr)) {
                if (isFourstate(exprp)) {
                    castFourstateWarn(exprp);
                    AstNodeExpr* const newp = getTwoStateCast(exprp);
                    exprp->replaceWith(newp);
                    pushDeletep(exprp);
                    nodep = newp;
                }
            }
        }
    }

    void visit(AstCStmtUser* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        cArgsHandler(nodep->nodesp());
    }
    void visit(AstCExprUser* const nodep) override { cArgsHandler(nodep->nodesp()); }
    void visit(AstCExpr* const nodep) override { cArgsHandler(nodep->nodesp()); }
    void visit(AstSFormatF* const nodep) override {
        for (AstNodeExpr* exprp = nodep->exprsp(); exprp;
             exprp = VN_AS(exprp->nextp(), NodeExpr)) {
            if (isFourstate(exprp)) {
                if (AstSFormatArg* const sformatArgp = VN_CAST(exprp, SFormatArg)) {
                    switch (sformatArgp->formatAttr()) {
                    case VFormatAttr::SIGNED:
                        sformatArgp->formatAttr(VFormatAttr::SIGNED_FOURSTATE);
                        break;
                    case VFormatAttr::UNSIGNED:
                        sformatArgp->formatAttr(VFormatAttr::UNSIGNED_FOURSTATE);
                        break;
                    default: exprp->v3fatalSrc("Expected a four-state");
                    }
                    AstNodeExpr* const currentExprp = sformatArgp->exprp();
                    currentExprp->replaceWith(new AstFourstateExpr{
                        currentExprp->fileline(), getFourstateExpressionValue(currentExprp),
                        getFourstateExpressionXZ(currentExprp)});
                    currentExprp->deleteTree();
                } else {
                    FileLine* const flp = exprp->fileline();
                    AstNodeExpr* const newp = new AstSFormatArg{
                        flp, VFormatAttr::UNSIGNED_FOURSTATE,
                        new AstFourstateExpr{flp, getFourstateExpressionValue(exprp),
                                             getFourstateExpressionXZ(exprp)}};
                    exprp->replaceWith(newp);
                    pushDeletep(exprp);
                    exprp = newp;
                }
                { FourstateLogicTypePropagator{nodep}; }
            }
        }
        iterateChildren(nodep);
    }
    void visit(AstPin* const nodep) override {
        AstVar* const varp = nodep->modVarp();
        if (!(varp->fourstateComplementp() || varp->isFourstateComplement())) {
            if (AstNodeExpr* const exprp = VN_CAST(nodep->exprp(), NodeExpr)) {
                if (!(VN_IS(exprp, NodeVarRef) || VN_IS(exprp, Const))
                    && varp->direction().isOutput()) {
                    // Output lvalues need a procedural statement to own index captures.
                    // Connect the child to a simple temporary, then copy its output to
                    // the original lvalue whenever the value or selection changes.
                    FileLine* const flp = nodep->fileline();
                    AstVar* const tmpVarp
                        = new AstVar{flp, VVarType::PORT, m_tmpNames.get(nodep), varp->dtypep()};
                    tmpVarp->noReset(true);
                    tmpVarp->lifetime(VLifetime::STATIC_EXPLICIT);
                    m_modp->addStmtsp(tmpVarp);
                    AstAlways* const alwaysp
                        = new AstAlways{flp, VAlwaysKwd::ALWAYS_COMB, nullptr,
                                        new AstAssign{flp, exprp->unlinkFrBack(),
                                                      new AstVarRef{flp, tmpVarp, VAccess::READ}}};
                    m_modp->addStmtsp(alwaysp);
                    nodep->exprp(new AstVarRef{flp, tmpVarp, VAccess::WRITE});
                    FourstateLogicTypePropagator{alwaysp};
                    FourstateLogicTypePropagator{nodep};
                    iterate(nodep);
                    return;
                }
                const bool exprFourstate = isFourstate(exprp);
                if (!(needsSplitting(varp->dtypep()) || exprFourstate)) {
                    iterateChildren(nodep);
                    return;
                }
                AstNodeExpr* exprValuep;
                AstNodeExpr* exprXZp;
                if (!(VN_IS(exprp, NodeVarRef) || VN_IS(exprp, Const))
                    && nodep->modVarp()->direction().isNonOutput()) {
                    // FIXME - this shall be completly refactored to sth like:
                    // form:
                    //   Pin(foo())
                    // to:
                    //  assign v = foo();
                    //  Pin(v)
                    FileLine* const flp = nodep->fileline();
                    AstNodeDType* const dtypep = needsSplitting(nodep->modVarp()->dtypep())
                                                     ? nodep->modVarp()->dtypep()
                                                     : exprp->dtypep();
                    AstVar* const tmpVarp
                        = new AstVar{flp, VVarType::PORT, m_tmpNames.get(nodep), dtypep};
                    tmpVarp->noReset(true);
                    tmpVarp->lifetime(VLifetime::STATIC_EXPLICIT);
                    m_modp->addStmtsp(tmpVarp);
                    splitVar(tmpVarp);

                    AstAlways* const alwaysp = new AstAlways{
                        flp, VAlwaysKwd::ALWAYS_COMB, nullptr,
                        new AstAssign{flp, new AstVarRef{flp, tmpVarp, VAccess::WRITE},
                                      exprp->unlinkFrBack()}};
                    { FourstateLogicTypePropagator{alwaysp}; }
                    m_modp->addStmtsp(alwaysp);
                    exprValuep = new AstVarRef{flp, getSplittedValue(tmpVarp), VAccess::READ};
                    exprXZp = new AstVarRef{flp, getSplittedXZ(tmpVarp), VAccess::READ};
                } else {
                    exprValuep = getFourstateExpressionValue(exprp);
                    exprXZp = getFourstateExpressionXZ(exprp);
                    exprp->unlinkFrBack()->deleteTree();
                }
                if (needsSplitting(varp->dtypep())) {
                    AstPin* const newp = new AstPin{
                        nodep->fileline(), nodep->pinNum(),
                        nodep->name().empty() ? "" : nodep->name() + FOURSTATE_XZ_SUFFIX, exprXZp};
                    nodep->addNextHere(newp);
                    nodep->exprp(exprValuep);
                    splitVar(varp);  // Ensure that variable is splitted
                    nodep->modVarp(getSplittedValue(varp));
                    newp->modVarp(getSplittedXZ(varp));
                } else if (exprFourstate) {
                    switch (varp->direction()) {
                    case VDirection::INPUT:
                        nodep->exprp(getTwoStateCast(exprValuep, exprXZp));
                        break;
                    case VDirection::OUTPUT:
                        m_modp->addStmtsp(
                            new AstAlways{nodep->fileline(), VAlwaysKwd::ALWAYS, nullptr,
                                          new AstAssign{nodep->fileline(), exprXZp,
                                                        createZeroOrOnesp(exprValuep)}});
                        nodep->exprp(exprValuep);
                        break;
                    default:
                        exprValuep->deleteTree();
                        exprXZp->deleteTree();
                        nodep->v3warn(E_UNSUPPORTED, "Unsupported: Ports with direction other "
                                                     "than INPUT and OUTPUT with --fourstate");
                        break;
                    }
                }
            } else if (!nodep->exprp() && needsSplitting(varp->dtypep())) {
                AstPin* const newp = new AstPin{
                    nodep->fileline(), nodep->pinNum(),
                    nodep->name().empty() ? "" : nodep->name() + FOURSTATE_XZ_SUFFIX, nullptr};
                nodep->addNextHere(newp);
                splitVar(varp);  // Ensure that variable is splitted
                nodep->modVarp(getSplittedValue(varp));
                newp->modVarp(getSplittedXZ(varp));
            }
        }
        iterateChildren(nodep);
    }
    void visit(AstNodeFTaskRef* const nodep) override {
        if (!isFTaskRefHandled(nodep)) {
            setFTaskRefHandled(nodep);
            size_t currentArgIdx = 0;
            const FTaskPortsHelper& fTaskPortsHelper = getFTaskPortHelper(nodep->taskp());
            for (AstArg* argp = nodep->argsp(); argp; argp = VN_AS(argp->nextp(), Arg)) {
                AstVar* const varp = fTaskPortsHelper.getArgPortVar(argp->name(), currentArgIdx);
                ++currentArgIdx;
                if (needsSplitting(varp->dtypep())) {
                    AstArg* const newp = new AstArg{
                        argp->fileline(),
                        argp->name().empty() ? "" : (varp->name() + FOURSTATE_XZ_SUFFIX),
                        getFourstateExpressionXZ(argp->exprp())};
                    argp->addNextHere(newp);
                    AstNodeExpr* const oldp = argp->exprp()->unlinkFrBack();
                    pushDeletep(oldp);
                    argp->exprp(getFourstateExpressionValue(oldp));
                    if (!argp->name().empty()) argp->name(argp->name() + FOURSTATE_VALUE_SUFFIX);
                    argp = VN_AS(argp->nextp(), Arg);
                } else if (isFourstate(argp->exprp())) {
                    AstNodeExpr* const oldp = argp->exprp()->unlinkFrBack();
                    pushDeletep(oldp);
                    argp->exprp(getTwoStateCast(oldp));
                }
            }
        }
        iterateChildren(nodep);
    }
    void visit(AstCastWrap* const nodep) override {
        if (!isFourstate(nodep) && isFourstate(nodep->lhsp())) {
            AstNodeExpr* const lhsp = nodep->lhsp()->unlinkFrBack();
            pushDeletep(lhsp);
            nodep->lhsp(getTwoStateCast(lhsp));
        }
        iterateChildren(nodep);
    }
    void visit(AstIToRD* const nodep) override {
        if (isFourstate(nodep->lhsp())) {
            AstNodeExpr* const lhsp = nodep->lhsp()->unlinkFrBack();
            pushDeletep(lhsp);
            nodep->lhsp(getTwoStateCast(lhsp));
        }
        iterateChildren(nodep);
    }
    void visit(AstISToRD* const nodep) override {
        if (isFourstate(nodep->lhsp())) {
            AstNodeExpr* const lhsp = nodep->lhsp()->unlinkFrBack();
            pushDeletep(lhsp);
            nodep->lhsp(getTwoStateCast(lhsp));
        }
        iterateChildren(nodep);
    }
    void visit(AstEqCase* const nodep) override {
        FileLine* const flp = nodep->fileline();
        AstNodeExpr* newp;
        if (isFourstate(nodep->lhsp()) && isFourstate(nodep->rhsp())) {
            newp = new AstAnd{flp,
                              new AstEq{flp, getFourstateExpressionXZ(nodep->lhsp()),
                                        getFourstateExpressionXZ(nodep->rhsp())},
                              new AstEq{flp, getFourstateExpressionValue(nodep->lhsp()),
                                        getFourstateExpressionValue(nodep->rhsp())}};
        } else if (isFourstate(nodep->lhsp()) || isFourstate(nodep->rhsp())) {
            AstNodeExpr* const fourstateHsp
                = isFourstate(nodep->lhsp()) ? nodep->lhsp() : nodep->rhsp();
            AstNodeExpr* const twostateHsp = isFourstate(nodep->lhsp())
                                                 ? nodep->rhsp()->unlinkFrBack()
                                                 : nodep->lhsp()->unlinkFrBack();
            newp = new AstAnd{
                flp, new AstNot{flp, getFourstateExpressionXZ(fourstateHsp)},
                new AstEq{flp, getFourstateExpressionValue(fourstateHsp), twostateHsp}};
        } else {
            newp = new AstEq{flp, nodep->lhsp()->unlinkFrBack(), nodep->rhsp()->unlinkFrBack()};
        }
        { FourstateLogicTypePropagator{newp}; }
        VNRelinker relinker;
        nodep->unlinkFrBack(&relinker);
        pushDeletep(nodep);
        relinker.relink(newp);
    }
    void visit(AstNeqCase* const nodep) override {
        FileLine* const flp = nodep->fileline();
        AstNodeExpr* newp;
        if (isFourstate(nodep->lhsp()) && isFourstate(nodep->rhsp())) {
            newp = new AstRedOr{
                flp, new AstOr{flp,
                               new AstXor{flp, getFourstateExpressionValue(nodep->lhsp()),
                                          getFourstateExpressionValue(nodep->rhsp())},
                               new AstXor{flp, getFourstateExpressionXZ(nodep->lhsp()),
                                          getFourstateExpressionXZ(nodep->rhsp())}}};
        } else if (isFourstate(nodep->lhsp()) || isFourstate(nodep->rhsp())) {
            AstNodeExpr* const fourstateHsp
                = isFourstate(nodep->lhsp()) ? nodep->lhsp() : nodep->rhsp();
            AstNodeExpr* const twostateHsp = isFourstate(nodep->lhsp())
                                                 ? nodep->rhsp()->unlinkFrBack()
                                                 : nodep->lhsp()->unlinkFrBack();
            newp = new AstRedOr{
                flp, new AstOr{
                         flp, getFourstateExpressionXZ(fourstateHsp),
                         new AstXor{flp, getFourstateExpressionValue(fourstateHsp), twostateHsp}}};
        } else {
            newp = new AstNeq{flp, nodep->lhsp()->unlinkFrBack(), nodep->rhsp()->unlinkFrBack()};
        }
        { FourstateLogicTypePropagator{newp}; }
        VNRelinker relinker;
        nodep->unlinkFrBack(&relinker);
        pushDeletep(nodep);
        relinker.relink(newp);
    }

    void visit(AstIsUnknown* const nodep) override {
        FileLine* const flp = nodep->fileline();
        AstNodeExpr* newp;
        if (isFourstate(nodep->lhsp())) {
            if (nodep->lhsp()->isPure()) {
                newp = new AstRedOr{flp, getFourstateExpressionXZ(nodep->lhsp())};
            } else {
                newp = new AstExprStmt{
                    flp, new AstStmtExpr{flp, getFourstateExpressionValue(nodep->lhsp())},
                    new AstRedOr{flp, getFourstateExpressionXZ(nodep->lhsp())}};
            }
        } else if (nodep->lhsp()->isPure()) {
            newp = createZeroOrOnesp(nodep);
        } else {
            AstNodeExpr* const lhsp = nodep->lhsp()->unlinkFrBack();
            newp = new AstRedOr{flp, new AstAnd{flp, lhsp, createZeroOrOnesp(lhsp)}};
        }
        FourstateLogicTypePropagator{newp};
        nodep->replaceWith(newp);
        pushDeletep(nodep);
    }

    void visit(AstCountOnes* const nodep) override {
        if (isFourstate(nodep->lhsp())) {
            AstNodeExpr* const lhsp = nodep->lhsp();
            lhsp->replaceWith(getTwoStateCast(lhsp));
            lhsp->deleteTree();
        }
        iterateChildren(nodep);
    }

    void visit(AstSel* const nodep) override {
        UASSERT_OBJ(!isFourstate(nodep), nodep,
                    "This visitor shall never be reached for four-state AstSel");
        if (!isSelpHandled(nodep)) {
            setSelpHandled(nodep);
            AstNodeExpr* const newp
                = getFourstateExpressionSelHandler(nodep, nodep->fromp()->cloneTree(false), true);
            { FourstateLogicTypePropagator{newp}; }
            VNRelinker relinker;
            nodep->unlinkFrBack(&relinker);
            pushDeletep(nodep);
            relinker.relink(newp);
        } else {
            iterateChildren(nodep);
        }
    }

    void visit(AstArraySel* const nodep) override {
        UASSERT_OBJ(!isFourstate(nodep), nodep,
                    "This visitor shall never be reached for four-state AstArraySel");
        if (!isSelpHandled(nodep) && isFixedIntegralArraySel(nodep)) {
            AstNodeExpr* const newp = getFourstateExpressionArraySelHandler(nodep, false);
            FourstateLogicTypePropagator{newp};
            nodep->replaceWith(newp);
            pushDeletep(nodep);
            return;
        }
        if (isFourstate(nodep->bitp())) {
            AstNodeExpr* const newp = getTwoStateCast(nodep->bitp());
            nodep->bitp()->unlinkFrBack()->deleteTree();
            nodep->bitp(newp);
        }
        iterateChildren(nodep);
    }

    void visit(AstLogOr* const nodep) override {
        if (!hasFourstateInSubtree(nodep->rhsp())) {
            iterateChildren(nodep);
            return;
        }
        UASSERT_OBJ(!isFourstate(nodep), nodep,
                    "This shall be reached only by two-state expressions");
        FileLine* const flp = nodep->fileline();
        AstVar* resultVarp = createTmp(nodep);
        addPrecalculation(new AstAssign{flp, new AstVarRef{flp, resultVarp, VAccess::WRITE},
                                        new AstRedOr{flp, nodep->lhsp()->unlinkFrBack()}});
        addPrecalculation(
            new AstIf{flp, new AstNot{flp, new AstVarRef{flp, resultVarp, VAccess::READ}},
                      new AstAssign{flp, new AstVarRef{flp, resultVarp, VAccess::WRITE},
                                    new AstRedOr{flp, nodep->rhsp()->unlinkFrBack()}}});
        AstVarRef* const newp = new AstVarRef{flp, resultVarp, VAccess::READ};
        setFourstate(newp, false);
        VNRelinker relinker;
        nodep->unlinkFrBack(&relinker);
        pushDeletep(nodep);
        relinker.relink(newp);
    }
    void visit(AstLogAnd* const nodep) override {
        if (!hasFourstateInSubtree(nodep->rhsp())) {
            iterateChildren(nodep);
            return;
        }
        UASSERT_OBJ(!isFourstate(nodep), nodep,
                    "This shall be reached only by two-state expressions");
        FileLine* const flp = nodep->fileline();
        AstVar* resultVarp = createTmp(nodep);
        addPrecalculation(new AstAssign{flp, new AstVarRef{flp, resultVarp, VAccess::WRITE},
                                        new AstRedOr{flp, nodep->lhsp()->unlinkFrBack()}});
        addPrecalculation(
            new AstIf{flp, new AstVarRef{flp, resultVarp, VAccess::READ},
                      new AstAssign{flp, new AstVarRef{flp, resultVarp, VAccess::WRITE},
                                    new AstRedOr{flp, nodep->rhsp()->unlinkFrBack()}}});
        AstVarRef* const newp = new AstVarRef{flp, resultVarp, VAccess::READ};
        setFourstate(newp, false);
        VNRelinker relinker;
        nodep->unlinkFrBack(&relinker);
        pushDeletep(nodep);
        relinker.relink(newp);
    }
    void visit(AstCond* const nodep) override {
        UASSERT_OBJ(!isFourstate(nodep), nodep,
                    "This shall be reached only by two-state expressions");
        if (isFourstate(nodep->condp())) {
            nodep->v3warn(E_UNSUPPORTED, "Unsupported: Conditional expression with four-state "
                                         "condition and non-integral result with --fourstate");
            return;
        }
        if (!hasFourstateInSubtree(nodep->thenp()) && !hasFourstateInSubtree(nodep->elsep())) {
            iterateChildren(nodep);
            return;
        }
        FileLine* const flp = nodep->fileline();
        AstVar* resultVarp = createTmp(nodep);
        addPrecalculation(
            new AstIf{flp, nodep->condp()->unlinkFrBack(),
                      new AstAssign{flp, new AstVarRef{flp, resultVarp, VAccess::WRITE},
                                    nodep->thenp()->unlinkFrBack()},
                      new AstAssign{flp, new AstVarRef{flp, resultVarp, VAccess::WRITE},
                                    nodep->elsep()->unlinkFrBack()}});
        AstVarRef* const newp = new AstVarRef{flp, resultVarp, VAccess::READ};
        setFourstate(newp, false);
        VNRelinker relinker;
        nodep->unlinkFrBack(&relinker);
        pushDeletep(nodep);
        relinker.relink(newp);
    }
    // Skip these trees since these expressions are not supported anyway
    // LCOV_EXCL_START
    void visit(AstCvtPackedToArray* const) override {}
    void visit(AstTestPlusArgs* const) override {}
    void visit(AstValuePlusArgs* const) override {}
    void visit(AstFOpenMcd* const) override {}
    void visit(AstConsPackUOrStruct* const) override {}
    // LCOV_EXCL_STOP

    void visit(AstNodeFTask* const nodep) override {
        VL_RESTORER(m_currentTmpSpotp);
        VL_RESTORER_CLEAR(m_tmpUnusedVarps);
        VL_RESTORER(m_tmpFuncLocal);
        m_tmpFuncLocal = true;
        m_currentTmpSpotp = nodep->stmtsp();
        TmpVarsReleaser releaser{*this, nodep};
        // Make sure FTasks use only local variables - prevents using tmp
        // which may be used by a caller
        for (auto& it : m_tmpUnusedVarps) it.clear();
        iterateChildren(nodep);
    }
    void visit(AstVar* const nodep) override {
        if (AstDelay* const delayp = nodep->delayp()) {
            if (!delayp->lhsp()->isPure()
                || (delayp->fallDelay() && !delayp->fallDelay()->isPure())) {
                delayp->v3warn(E_UNSUPPORTED,
                               "Unsupported: Impure net delay expression with --fourstate");
                pushDeletep(delayp->unlinkFrBack());
            }
        }
        if (VL_UNLIKELY(!isDTypepSupported(nodep->dtypep()->skipRefp()).first)) {
            nodep->v3warn(E_UNSUPPORTED,
                          "Unsupported: Variable of type: " << nodep->dtypep()->prettyDTypeNameQ()
                                                            << " with --fourstate");
        } else if (needsSplitting(nodep->dtypep())) {
            splitVar(nodep);
        }
        iterateChildren(nodep);
    }
    void visit(AstPull* const nodep) override {
        nodep->v3warn(E_UNSUPPORTED,
                      "Unsupported: Pullups and pulldowns are unsupported with --fourstate");
    }

    void visit(AstModport* const nodep) override {
        for (AstNode* modportVarp = nodep->varsp(); modportVarp;
             modportVarp = modportVarp->nextp()) {
            AstModportVarRef* const varrefp = VN_AS(modportVarp, ModportVarRef);
            if (AstVar* const varp = varrefp->varp()) {
                if (needsSplitting(varp->dtypep())) {
                    splitVar(varp);
                    AstVar* const valueVarp = getValuePartVarp(varp);
                    AstVar* const xzVarp = getSplittedXZ(varp);
                    varrefp->varp(valueVarp);
                    varrefp->name(valueVarp->name());
                    AstModportVarRef* const xzp = new AstModportVarRef{
                        varrefp->fileline(), xzVarp->name(), varrefp->direction()};
                    xzp->varp(xzVarp);
                    varrefp->addNextHere(xzp);
                    modportVarp = xzp;
                }
            }
        }
    }

    void visit(AstModportVarRef* const nodep) override { iterateChildren(nodep); }

    void visit(AstNodeModule* const nodep) override {
        VL_RESTORER(m_currentTmpSpotp);
        VL_RESTORER(m_modp);
        VL_RESTORER_COPY(m_tmpUnusedVarps);
        VL_RESTORER_CLEAR(m_arrayIndexCaptures);
        m_modp = nodep;
        m_currentTmpSpotp = nodep->stmtsp();
        iterateChildren(nodep);
    }
    void visit(AstNodeStmt* const nodep) override {
        StmtHelper stmtHelper{*this, nodep};
        iterateChildren(nodep);
    }
    void visit(AstNode* const nodep) override { iterateChildren(nodep); }

public:
    explicit FourstateVisitor(AstNetlist* const netlistp)
        : m_tmpNames{"__VfourstateTmp"}
        , m_pinHelpersNames{"__VpinHelper"}
        , m_fourstateGeneratorValueVisitor{*this}
        , m_fourstateGeneratorXZVisitor{*this} {
        m_pullAssignments = FourstatePullVisitor::collect(netlistp);
        V3Error::abortIfErrors();
        { FourstateLogicTypePropagator{netlistp}; }
        iterate(netlistp);
        m_pullAssignments.clear();  // Original assignment pointers are no longer needed.
        V3Error::abortIfErrors();
        triorTriandReduce(m_assignWToTriand, triandReducer);
        triorTriandReduce(m_assignWToTrior, triorReducer);
        triorTriandReduce(m_assignWToWire, triReducer);
        V3Error::abortIfErrors();
        // Split variables are obsolete. Audit only their lowered replacements, including
        // parameter initializers. Keep the originals alive until deferred deletion so
        // any missed reference is still diagnosed rather than dereferencing freed storage.
        for (AstVar* const varp : m_varpsToRemove) pushDeletep(varp->unlinkFrBack());
        m_varpsToRemove.clear();
        { FourstateLogicTypePropagator{netlistp}; }
        netlistp->foreach([](const AstNodeExpr* const nodep) {
            if (VN_IS(nodep, NodeFTaskRef)) {
                // Changing it in type propagator is unnecessary since those will be 100% handled
                return;
            }
            if (isFourstate(nodep)) {
                nodep->v3warn(E_UNSUPPORTED,
                              "Unsupported: This four-state expression has not been handled");
            }
        });
        V3Error::abortIfErrors();
        UASSERT_OBJ(m_tmpVarReleaserStack.empty(), m_tmpVarReleaserStack.back().first,
                    "TmpVarsReleaser stack frame has not been consumed");
    }
    ~FourstateVisitor() override {
        V3Stats::addStat("Fourstate, Implicit pull driver fallbacks", m_statPullFallbacks);
    }
};

void V3Fourstate::fourstateAll(AstNetlist* netlistp) {
    UINFO(2, __FUNCTION__ << ":");
    { FourstateVisitor{netlistp}; }
    v3Global.setFourstateHandled();
    V3Global::dumpCheckGlobalTree("fourstate", 0, dumpTreeEitherLevel() >= 6);
}
