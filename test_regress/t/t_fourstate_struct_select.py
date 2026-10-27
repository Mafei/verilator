#!/usr/bin/env python3
# DESCRIPTION: Verilator: Variable writes through unpacked two-state struct fields
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
test.compile(verilator_flags2=['--binary', '--fourstate', '-Wno-FUTURE', '--debug-check'])
test.execute()
for width in (7, 15, 31, 33, 65, 95):
    count = 184 if width >= 65 else 180
    test.file_grep(test.run_log_filename, f'^Struct selection W={width} checks={count}$')
test.file_grep_count(test.run_log_filename, r'^Struct selection W=', 6)
test.file_grep(test.run_log_filename, r'^Struct selection profiles: 6$')
test.passes()
