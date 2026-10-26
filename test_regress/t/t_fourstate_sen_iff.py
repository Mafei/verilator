#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
test.compile(verilator_flags2=['--binary', '--trace', '--fourstate', '-Wno-FUTURE'])
test.execute()
test.file_grep(test.run_log_filename, r'^Sensitivity iff checks: (\d+)$', 36)
expected = {
    't.hits': [(0, 0), (3, 1), (5, 2), (7, 3), (13, 4), (15, 5), (21, 6), (23, 7)],
    't.unknown_hits': [(0, 0), (9, 1), (11, 2), (13, 3), (15, 4), (17, 5), (19, 6), (21, 7),
                       (23, 8)],
    't.edges': [(0, 0), (1, 1), (3, 2), (5, 3), (7, 4), (9, 5), (11, 6), (13, 7), (15, 8), (17, 9),
                (19, 10), (21, 11), (23, 12)],
}
expected = {
    name: [(time, format(value, '032b')) for time, value in values]
    for name, values in expected.items()
}
check_trace(test, expected, {name: 32 for name in expected})
test.passes()
