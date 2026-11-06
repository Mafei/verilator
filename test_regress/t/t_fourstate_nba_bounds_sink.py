#!/usr/bin/env python3
# DESCRIPTION: Verilator: Delayed class NBA bounds controls
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from nba_bounds_sink_oracle import check

test.scenarios('vlt')
test.compile(
    verilator_flags2=['--binary', '--trace', '--fourstate', '--sched-zero-delay', '-Wno-FUTURE'])
test.execute()
test.file_grep(test.run_log_filename, r'CLASS_NBA_BOUNDS_PASS checks=(\d+)', 10)
test.file_grep_not(test.run_log_filename, r'%Error|%Warning')
try:
    result = check(test.trace_filename)
except ValueError as error:
    test.error(str(error))
else:
    print(f'Class bounds trace checks: {result["transitions"]}')
test.passes()
