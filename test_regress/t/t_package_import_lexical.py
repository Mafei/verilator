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
test.compile(verilator_flags2=["--binary", "--debug-check", "--debugi-V3ImportLexical 3"])
test.execute()

filename = Path(test.obj_dir) / (test.vm_prefix + "__import_lexical.json")
capture = json.loads(filename.read_text())
if capture['schema'] != 'explicit-variable-import-prototype-v1':
    test.error('Unexpected lexical import view schema')
modules = {entry['name']: entry for entry in capture['modules']}
for name in ('lexical_scope', 'lexical_generate'):
    if not modules[name]['supported']:
        test.error(f'Expected complete source qualification of {name}: {modules[name]["reason"]}')
if modules['t']['supported'] or capture['wildcardExportSupported']:
    test.error('Lexical subset must not claim cell or wildcard/export query support')
for marker in ('IMPORT_LEXICAL tag=0 checks=11', 'IMPORT_LEXICAL tag=1 checks=11',
               'IMPORT_LEXICAL generate checks=3'):
    test.file_grep_count(test.run_log_filename, '^' + marker + '$', 1)

test.passes()
