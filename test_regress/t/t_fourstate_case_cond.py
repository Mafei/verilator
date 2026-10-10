#!/usr/bin/env python3
# DESCRIPTION: Verilator: Four-state conditional and indexed case items
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
test.compile(verilator_flags2=[
    '--binary', '--fourstate', '--trace', '--debug-check', '-Wno-FUTURE', '-Wno-fatal'
])
test.execute()
test.file_grep(test.run_log_filename, r'^Case item checks: (\d+)$', 31)
# Literal histories at physical timestamps; these do not infer event-region order.
expected = {
    't.branch_hit': [(0, '0'), (1, '1'), (2, '0'), (4, '1'), (5, '0'), (10, '1'), (11, '0'),
                     (14, '1'), (15, '0')],
    't.unknown_hit': [(0, '0'), (18, '1')],
    't.zero_hit': [(0, '1'), (17, '0')],
    't.one_hit': [(0, '0'), (17, '1'), (18, '0')],
}
check_trace(test, expected, {name: 1 for name in expected})
test.passes()
