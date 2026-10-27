#!/usr/bin/env python3
# DESCRIPTION: Verilator: Packed indices use element widths in diagnostics
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from pathlib import Path

test.scenarios('vlt')
test.lint(verilator_flags2=['--debug-check'])
Path(test.compile_log_filename).rename(test.obj_dir + '/two_state_compile.log')
test.lint(verilator_flags2=[
    '--fourstate', '-Wno-FUTURE', '--debug-check', '--dumpi-tree-json', '9', '--dumpi-tree', '9'
])
for dump in test.glob_some(test.obj_dir + '/*_width.tree.json'):
    test.file_grep(dump, r'"declIndexWidth"\s*:\s*32')
    test.file_grep(dump, r'"declIndexWidthMin"\s*:\s*[1-9]')
test.passes()
