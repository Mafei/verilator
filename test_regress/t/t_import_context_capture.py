#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import json
from pathlib import Path

import vltest_bootstrap

test.scenarios('vlt')
test.lint(v_flags=["--debugi-V3ImportContext 3", "--debug-check"])

filename = Path(test.obj_dir) / (test.vm_prefix + "__import_context.json")
capture = json.loads(filename.read_text())
if (capture['schema'] != 'import-context-capture-v1' or capture['bindingsProvided']
        or capture['cloneBindingsProvided'] or capture['queryRolesClassified']
        or capture['syntheticImportsCaptured']):
    test.error('Capture-only ledger must not claim semantic or clone bindings')
events = capture['events']
if [event['ordinal'] for event in events] != list(range(len(events))):
    test.error('Parser event ordinals are not contiguous')


def one(kind, name, scope=None):
    found = [
        event for event in events if event['kind'] == kind and event['name'] == name and (
            scope is None or event['scope'] == scope)
    ]
    if len(found) != 1:
        test.error(f'Expected one {kind} event for {name}, got {len(found)}')
    return found[0]


module = one('ENTER_SCOPE', 'capture_scope')
before = one('ENTER_SCOPE', 'before_f')
after = one('ENTER_SCOPE', 'after_f')
edge = one('IMPORT', 'entries', module['scope'])
before_use = one('SYNTAX', 'entries', before['scope'])
after_use = one('SYNTAX', 'entries', after['scope'])
if (before_use['ordinal'] >= edge['ordinal'] or edge['ordinal'] >= after_use['ordinal']):
    test.error('Repeated include expansion/import order was lost')
if (before['parentScope'] != module['scope'] or after['parentScope'] != module['scope']
        or before['parentCut'] >= edge['ordinal'] or after['parentCut'] < edge['ordinal']):
    test.error('Function source parent cuts do not straddle the import')
if edge['package'] != 'capture_pkg':
    test.error('Receiver import edge lost its source package')

unit_declaration = one('SYNTAX', 'entries', 1)
unit_edge = one('IMPORT', 'TOKEN', 1)
top = one('ENTER_SCOPE', 't')
if (unit_declaration['ordinal'] >= module['ordinal'] or module['ordinal'] >= unit_edge['ordinal']
        or unit_edge['ordinal'] >= top['ordinal']):
    test.error('Unit items/module descriptions lost their parser interleaving')
if top['parentScope'] != 1 or top['parentCut'] < unit_edge['ordinal']:
    test.error('Later module lost the compilation-unit entry cut')

test.passes()
