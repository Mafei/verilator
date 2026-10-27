// -*- mode: C++; c-file-style: "cc-mode" -*-
//*************************************************************************
// DESCRIPTION: Source views for a bounded explicit variable-import prototype.
//
// Code available from: https://verilator.org
//
// SPDX-FileCopyrightText: 2026 Mafei
// SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
//*************************************************************************

#ifndef VERILATOR_V3IMPORTLEXICAL_H_
#define VERILATOR_V3IMPORTLEXICAL_H_

#include "config_build.h"
#include "verilatedos.h"

#include <map>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

class AstNode;
class ImportLexicalAnnotator;

class V3ImportLexical final {
    friend class ImportLexicalAnnotator;

public:
    struct Import final {
        uint32_t view = 0;
        std::string package;
    };
    struct Scope final {
        bool unit = false;
        bool needsSymbol = false;
        std::map<std::string, std::vector<Import>> imports;
    };
    struct View final {
        uint32_t scope = 0;
        uint32_t outer = 0;
        uint32_t unitCut = 0;
    };

private:
    struct Eligibility final {
        std::string module;
        std::string reason;
    };
    struct Package final {
        bool direct = false;
        std::unordered_set<std::string> variables;
    };
    // IDs, strings and value records only; no pointer survives a link graph rebuild.
    std::vector<Scope> m_scopes;
    std::vector<View> m_views;
    std::vector<Eligibility> m_eligibility;
    std::unordered_map<std::string, uint32_t> m_unitDeclarations;
    std::unordered_map<std::string, Package> m_packages;
    std::unordered_set<std::string> m_descriptionNames;
    uint32_t m_description = 0;
    std::string m_unitUnsupported;

public:
    V3ImportLexical();
    void sourceDescription(AstNode* nodep, bool list) VL_MT_DISABLED;
    const Scope& scope(uint32_t id) const;
    const View& view(uint32_t id) const;
    bool unitDeclarationVisible(const std::string& name, uint32_t cut) const;
    bool directVariable(const std::string& package, const std::string& name) const;
    const std::string* importedPackage(uint32_t viewId, const std::string& name) const;
    static uint32_t scopeId(const AstNode* nodep);
    static void scopeId(AstNode* nodep, uint32_t id);
    void dump() const VL_MT_DISABLED;
};

#endif  // guard
