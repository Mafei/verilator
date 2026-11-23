#!/usr/bin/env python3
# DESCRIPTION: Verilator: Trace writes after a split coroutine resumes
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
test.top_filename = 't/t_unconnected_pull_bits.v'
test.compile(make_main=False,
             make_top_shell=False,
             verilator_flags2=['--binary', '--debug-check', '--fourstate', '-Wno-FUTURE'])
test.execute()
for width in (7, 33, 65, 34):
    test.file_grep_count(test.obj_dir + '/vlt_sim.log',
                         rf'^PULL_BITS width={width} samples=4 per_bit=1 controls=1$', 1)
test.passes()
