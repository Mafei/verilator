// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// DESCRIPTION: Capture explicit-variable import views before LinkParse reorders.
//   A complete source module is qualified before any query is annotated. Other
//   modules retain the old resolver. Views are immutable source-order cuts;
//   source IDs copy with AST clones, while lookup uses each instance's live graph.
//   Wildcard/export/type/member/interface and early semantic Find roles are outside
//   this prototype, rather than being resolved by a per-query eager-map fallback.
//
// Code available from: https://verilator.org
//
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
//*************************************************************************

#include "V3PchAstNoMT.h"  // VL_MT_DISABLED_CODE_UNIT

#include "V3ImportLexical.h"

#include "V3File.h"
#include "V3Global.h"

#include <algorithm>
#include <iterator>
#include <map>
#include <set>

VL_DEFINE_DEBUG_FUNCTIONS;

namespace {
bool isSourceScope(const AstNode* nodep) {
    return VN_IS(nodep, NodeModule) || VN_IS(nodep, NodeFTask) || VN_IS(nodep, NodeBlock)
           || VN_IS(nodep, GenBlock) || VN_IS(nodep, NodeForeach);
}

class ImportScopeMembers final : public VNVisitorConst {
    void visit(AstNode* nodep) override {
        if (isSourceScope(nodep)) {
            if (!nodep->name().empty()) declarations.insert(nodep->name());
            return;
        }
        if (const AstVar* const varp = VN_CAST(nodep, Var)) {
            declarations.insert(varp->name());
            return;
        }
        if (const AstPackageImport* const impp = VN_CAST(nodep, PackageImport)) {
            imports.push_back(impp);
            return;
        }
        iterateChildrenConst(nodep);
    }

public:
    std::set<std::string> declarations;
    std::vector<const AstPackageImport*> imports;
    explicit ImportScopeMembers(AstNode* nodep) { iterateChildrenConst(nodep); }
};

class ImportPackageCheck final : public VNVisitorConst {
    void visit(AstNode* nodep) override {
        if (VN_IS(nodep, PackageImport) || VN_IS(nodep, PackageExport)
            || VN_IS(nodep, PackageExportStarStar)) {
            clean = false;
        }
        iterateChildrenConst(nodep);
    }

public:
    bool clean = true;
    explicit ImportPackageCheck(AstNode* nodep) { iterateConst(nodep); }
};

class ImportUnitCheck final : public VNVisitorConst {
    void visit(AstNode* nodep) override {
        // Unit initializers/type expressions are not annotated by the module replay.
        // The initial subset admits only closed literal variable declarations there.
        if (!VN_IS(nodep, Var) && !VN_IS(nodep, BasicDType) && !VN_IS(nodep, PackArrayDType)
            && !VN_IS(nodep, UnpackArrayDType) && !VN_IS(nodep, Range) && !VN_IS(nodep, Const)) {
            clean = false;
        }
        iterateChildrenConst(nodep);
    }

public:
    bool clean = true;
    explicit ImportUnitCheck(AstNode* nodep) { iterateConst(nodep); }
};

class ImportIteratorCheck final : public VNVisitorConst {
    const V3ImportLexical& m_context;
    const std::set<std::string>& m_importNames;
    const std::set<std::string>& m_declarations;
    void visit(AstNodeForeach* nodep) override {
        for (AstNode* p = nodep->headerp()->elementsp(); p; p = p->nextp()) {
            if (m_importNames.count(p->name()) || m_declarations.count(p->name())
                || m_context.unitDeclarationVisible(p->name(), UINT32_MAX)) {
                clean = false;
            }
        }
        iterateChildrenConst(nodep);
    }
    void visit(AstNode* nodep) override { iterateChildrenConst(nodep); }

public:
    bool clean = true;
    ImportIteratorCheck(const V3ImportLexical& context, AstNode* nodep,
                        const std::set<std::string>& importNames,
                        const std::set<std::string>& declarations)
        : m_context{context}
        , m_importNames{importNames}
        , m_declarations{declarations} {
        iterateConst(nodep);
    }
};

class ImportLexicalQualifier final : public VNVisitorConst {
    const V3ImportLexical& m_context;
    std::set<std::string> m_importNames;
    std::set<std::string> m_declarations;
    bool m_inDType = false;

    bool directVariable(const AstPackageImport* impp) {
        return impp->name() != "*" && m_context.directVariable(impp->pkgName(), impp->name());
    }

    void visit(AstNode* nodep) override {
        if (!reason.empty()) return;
        VL_RESTORER(m_inDType);
        m_inDType = m_inDType || VN_IS(nodep, NodeDType);
        if (m_inDType && (VN_IS(nodep, ParseRef) || VN_IS(nodep, NodeFTaskRef))) {
            reason = "non-literal declaration type query";
            return;
        }
        if (VN_IS(nodep, RefDType) || VN_IS(nodep, ParamTypeDType) || VN_IS(nodep, Typedef)
            || VN_IS(nodep, TypedefFwd) || VN_IS(nodep, NodeUOrStructDType)
            || VN_IS(nodep, MemberDType) || VN_IS(nodep, EnumItem)
            || VN_IS(nodep, ClassOrPackageRef) || VN_IS(nodep, Dot) || VN_IS(nodep, MethodCall)
            || VN_IS(nodep, Class) || VN_IS(nodep, Iface) || VN_IS(nodep, Cell)
            || VN_IS(nodep, IfaceRefDType) || VN_IS(nodep, IfaceGenericDType)
            || VN_IS(nodep, Clocking) || VN_IS(nodep, ClockingItem)
            || VN_IS(nodep, Constraint) || VN_IS(nodep, With) || VN_IS(nodep, Disable)
            || VN_IS(nodep, PatMember) || VN_IS(nodep, Text) || VN_IS(nodep, DefParam)
            || VN_IS(nodep, Bind) || VN_IS(nodep, RandSequence) || VN_IS(nodep, CExpr)
            || VN_IS(nodep, CStmt) || VN_IS(nodep, DpiExport)
            || VN_IS(nodep, PackageExport) || VN_IS(nodep, AssignW)
            || VN_IS(nodep, Pull) || VN_IS(nodep, Implicit) || VN_IS(nodep, Port)
            || VN_IS(nodep, WithParse) || VN_IS(nodep, CoverWith) || VN_IS(nodep, CoverCrossWith)
            || VN_IS(nodep, Covergroup) || VN_IS(nodep, CoverpointRef)
            || VN_IS(nodep, NodeFuncCovItem) || VN_IS(nodep, SystemCSection)
            || VN_IS(nodep, AssertCtl)
            || VN_IS(nodep, PackageExportStarStar)) {
            reason = "unclosed query role: "s + nodep->typeName();
            return;
        }
        if (const AstVar* const varp = VN_CAST(nodep, Var)) {
            m_declarations.insert(varp->name());
            if (varp->isIO() || varp->isIfaceRef()) reason = "port/interface declaration";
        }
        if (const AstNodeVarRef* const refp = VN_CAST(nodep, NodeVarRef)) {
            if (!refp->varp() || VN_IS(refp, VarXRef)) reason = "unbound/hierarchical VarRef";
        }
        if (const AstNodeFTask* const taskp = VN_CAST(nodep, NodeFTask)) {
            if ((!VN_IS(taskp, Func) && !VN_IS(taskp, Task)) || taskp->isExternDef()
                || taskp->isExternProto() || taskp->prototype()
                || taskp->dpiImport() || taskp->dpiExport() || taskp->classOrPackagep()
                || !taskp->ifacePortName().empty()) {
                reason = "external/deferred function declaration";
            }
        }
        if (const AstNodeFTaskRef* const refp = VN_CAST(nodep, NodeFTaskRef)) {
            if (!refp->dotted().empty() || refp->classOrPackagep() || refp->withp()) {
                reason = "qualified/deferred function query";
            }
        }
        if (const AstParseRef* const refp = VN_CAST(nodep, ParseRef)) {
            if (refp->lhsp()) reason = "compound ParseRef";
        }
        if (isSourceScope(nodep)) {
            const ImportScopeMembers members{nodep};
            std::map<std::string, std::string> imported;
            for (const AstPackageImport* const impp : members.imports) {
                hasImports = true;
                if (!directVariable(impp)) {
                    reason = "non-direct-variable/wildcard/export import";
                    return;
                }
                if (members.declarations.count(impp->name())) {
                    reason = "local declaration/import conflict";
                    return;
                }
                const auto inserted = imported.emplace(impp->name(), impp->pkgName());
                if (!inserted.second && inserted.first->second != impp->pkgName()) {
                    reason = "different explicit sources for one name";
                    return;
                }
                m_importNames.insert(impp->name());
            }
        }
        if (!reason.empty()) return;
        iterateChildrenConst(nodep);
    }

public:
    std::string reason;
    bool hasImports = false;
    ImportLexicalQualifier(const V3ImportLexical& context, AstNode* nodep)
        : m_context{context} {
        iterateConst(nodep);
        if (reason.empty() && !hasImports) reason = "no explicit import in source module";
        if (reason.empty()) {
            // Find installs the iterators before linking the header expression.
            // Header/body shadowing needs a separate role-aware extension.
            const ImportIteratorCheck check{m_context, nodep, m_importNames, m_declarations};
            if (!check.clean) reason = "iterator/declaration or import name overlap";
        }
    }
};
}  // namespace

class ImportLexicalAnnotator final : public VNVisitor {
    V3ImportLexical& m_context;
    uint32_t m_view = 0;

    void visit(AstNode* nodep) override {
        if (isSourceScope(nodep)) {
            VL_RESTORER(m_view);
            const ImportScopeMembers members{nodep};
            const bool needsSymbol = VN_IS(nodep, NodeModule) || VN_IS(nodep, NodeFTask)
                                     || VN_IS(nodep, NodeForeach) || !nodep->name().empty()
                                     || !members.declarations.empty() || !members.imports.empty();
            const uint32_t scope = static_cast<uint32_t>(m_context.m_scopes.size());
            m_context.m_scopes.push_back(V3ImportLexical::Scope{false, needsSymbol, {}});
            V3ImportLexical::scopeId(nodep, scope);
            const uint32_t outer = m_view;
            m_view = static_cast<uint32_t>(m_context.m_views.size());
            m_context.m_views.push_back(V3ImportLexical::View{scope, outer, 0});
            iterateChildren(nodep);
        } else if (const AstPackageImport* const impp = VN_CAST(nodep, PackageImport)) {
            const V3ImportLexical::View previous = m_context.view(m_view);
            m_view = static_cast<uint32_t>(m_context.m_views.size());
            m_context.m_views.push_back(
                V3ImportLexical::View{previous.scope, previous.outer, 0});
            m_context.m_scopes[previous.scope].imports[impp->name()].push_back(
                V3ImportLexical::Import{m_view, impp->pkgName()});
        } else {
            if (AstParseRef* const refp = VN_CAST(nodep, ParseRef)) refp->importViewId(m_view);
            if (AstNodeFTaskRef* const refp = VN_CAST(nodep, NodeFTaskRef)) {
                refp->importViewId(m_view);
            }
            iterateChildren(nodep);
        }
    }

public:
    ImportLexicalAnnotator(V3ImportLexical& context, AstNode* nodep, uint32_t unitCut)
        : m_context{context} {
        m_view = static_cast<uint32_t>(context.m_views.size());
        context.m_views.push_back(V3ImportLexical::View{1, 0, unitCut});
        iterate(nodep);
    }
};

V3ImportLexical::V3ImportLexical() {
    m_scopes.push_back(Scope{});  // Zero denotes the unchanged resolver path
    m_scopes.push_back(Scope{true, true, {}});
    m_views.push_back(View{});
}

const V3ImportLexical::Scope& V3ImportLexical::scope(uint32_t id) const {
    UASSERT_STATIC(id && id < m_scopes.size(), "Invalid lexical source scope ID");
    return m_scopes[id];
}

const V3ImportLexical::View& V3ImportLexical::view(uint32_t id) const {
    UASSERT_STATIC(id && id < m_views.size(), "Invalid lexical import view ID");
    return m_views[id];
}

bool V3ImportLexical::unitDeclarationVisible(const std::string& name, uint32_t cut) const {
    const auto it = m_unitDeclarations.find(name);
    return it != m_unitDeclarations.end() && it->second <= cut;
}

bool V3ImportLexical::directVariable(const std::string& package, const std::string& name) const {
    const auto it = m_packages.find(package);
    return it != m_packages.end() && it->second.direct && it->second.variables.count(name);
}

const std::string* V3ImportLexical::importedPackage(uint32_t viewId,
                                                 const std::string& name) const {
    const Scope& sourceScope = scope(view(viewId).scope);
    const auto it = sourceScope.imports.find(name);
    if (it == sourceScope.imports.end()) return nullptr;
    const std::vector<Import>& imports = it->second;
    // Each name has its own ordered history: unrelated imports do not increase
    // query time, and later same-name imports cannot leak through an earlier cut.
    const auto bound = std::upper_bound(
        imports.begin(), imports.end(), viewId,
        [](uint32_t id, const Import& imported) { return id < imported.view; });
    return bound == imports.begin() ? nullptr : &std::prev(bound)->package;
}

uint32_t V3ImportLexical::scopeId(const AstNode* nodep) {
    if (const AstCell* const cellp = VN_CAST(nodep, Cell)) {
        return cellp->modp() ? cellp->modp()->importScopeId() : 0;
    }
    if (const AstNodeModule* const p = VN_CAST(nodep, NodeModule)) return p->importScopeId();
    if (const AstNodeFTask* const p = VN_CAST(nodep, NodeFTask)) return p->importScopeId();
    if (const AstNodeBlock* const p = VN_CAST(nodep, NodeBlock)) return p->importScopeId();
    if (const AstGenBlock* const p = VN_CAST(nodep, GenBlock)) return p->importScopeId();
    if (const AstNodeForeach* const p = VN_CAST(nodep, NodeForeach)) return p->importScopeId();
    return 0;
}

void V3ImportLexical::scopeId(AstNode* nodep, uint32_t id) {
    if (AstNodeModule* const p = VN_CAST(nodep, NodeModule)) p->importScopeId(id);
    else if (AstNodeFTask* const p = VN_CAST(nodep, NodeFTask)) p->importScopeId(id);
    else if (AstNodeBlock* const p = VN_CAST(nodep, NodeBlock)) p->importScopeId(id);
    else if (AstGenBlock* const p = VN_CAST(nodep, GenBlock)) p->importScopeId(id);
    else if (AstNodeForeach* const p = VN_CAST(nodep, NodeForeach)) p->importScopeId(id);
    else nodep->v3fatalSrc("Not a lexical source scope");
}

void V3ImportLexical::sourceDescription(AstNode* nodep, bool list) {
    ++m_description;
    if (!nodep) return;
    if (list) {
        for (AstNode* p = nodep; p; p = p->nextp()) {
            const ImportUnitCheck check{p};
            if (VN_IS(p, Var) && check.clean) {
                m_unitDeclarations.emplace(p->name(), m_description);
            } else {
                m_unitUnsupported = "unclosed compilation-unit declaration/import";
            }
        }
        return;
    }
    const bool unique = m_descriptionNames.insert(nodep->name()).second;
    if (!unique) m_packages[nodep->name()].direct = false;
    if (const AstPackage* const pkgp = VN_CAST(nodep, Package)) {
        const ImportPackageCheck check{nodep};
        Package& package = m_packages[nodep->name()];
        package.direct = unique && check.clean && pkgp->libname() == "work";
        for (const AstNode* p = pkgp->stmtsp(); p; p = p->nextp()) {
            if (VN_IS(p, Var)) package.variables.insert(p->name());
        }
        return;
    }
    const AstModule* const modp = VN_CAST(nodep, Module);
    if (!modp) return;
    std::string reason = m_unitUnsupported;
    if (modp->isProgram() || modp->isChecker() || modp->libname() != "work") {
        reason = "program/checker/non-work module";
    }
    if (v3Global.opt.hierarchical() || v3Global.opt.hierChild() || v3Global.opt.serializeOnly()) {
        reason = "hierarchical/serialized compilation";
    }
    if (v3Global.usesStdPackage()) reason = "synthetic compilation-unit std import";
    if (reason.empty()) {
        const ImportLexicalQualifier qualifier{*this, nodep};
        reason = qualifier.reason;
    }
    m_eligibility.push_back(Eligibility{nodep->name(), reason});
    if (!reason.empty()) return;
    const ImportLexicalAnnotator annotator{*this, nodep, m_description};
}

void V3ImportLexical::dump() const {
    if (debug() < 3) return;
    V3OutJsonFile of{v3Global.opt.hierTopDataDir() + "/" + v3Global.opt.prefix()
                     + "__import_lexical.json"};
    of.put("schema", "explicit-variable-import-prototype-v1");
    of.put("wildcardExportSupported", false);
    of.put("sourceScopes", static_cast<int>(m_scopes.size()) - 1);
    of.put("sourceViews", static_cast<int>(m_views.size()) - 1);
    of.begin("modules", '[');
    for (const Eligibility& entry : m_eligibility) {
        of.begin();
        of.put("name", entry.module);
        of.put("supported", entry.reason.empty());
        of.put("reason", entry.reason);
        of.end();
    }
    of.end();
}
