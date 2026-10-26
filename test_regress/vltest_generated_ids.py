# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Compare compiler-owned identifier hashes without changing SV payloads."""

import re

_TOKENS = re.compile(
    r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|\\[^\s]+'
    r'|(?P<identifier>\b(?P<prefix>__V(?:enum|repeatCount)_h)'
    r'(?P<hash>[0-9a-f]{8}|HASH[0-9]+)(?P<suffix>__[0-9]+)\b)', re.DOTALL)


def normalize_generated_identifiers(text):
    """Preserve suffixes, bindings, literals, comments and all other identifiers."""
    identities = {}
    tokens = {}

    def replace(match):
        if match.group('identifier') is None:
            return match.group()
        tokens[match.group()] = None
        prefix = match.group('prefix')
        namespace = identities.setdefault(prefix, {})
        original = match.group('hash')
        if original not in namespace:
            namespace[original] = 'HASH' + str(len(namespace))
        return prefix + namespace[original] + match.group('suffix')

    return _TOKENS.sub(replace, text), list(tokens), identities
