#!/usr/bin/env python3
# DESCRIPTION: Verilator: Wide-source scalar clipping runtime matrix
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
test.top_filename = 't/t_assignsel_clip_runtime.v'
test.pli_filename = 't/t_assignsel_clip_runtime.cpp'

test.compile(make_top_shell=False,
             make_main=False,
             threads=1,
             verilator_flags2=['--exe', test.pli_filename, '--no-timing', '-CFLAGS', '-std=c++14'])
test.execute()
test.file_grep(test.run_log_filename, r'Clipped scalar runtime checks: (\d+)', 3840)
test.file_grep_not(test.run_log_filename, r'%Error|%Warning')
test.passes()
