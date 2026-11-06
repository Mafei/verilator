#!/usr/bin/env python3
# DESCRIPTION: Verilator: No-timing NBA event delivery and capture control
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
test.top_filename = 't/t_nba_event_capture.v'
test.pli_filename = 't/t_nba_event_capture.cpp'

test.compile(make_top_shell=False,
             make_main=False,
             threads=1,
             verilator_flags2=[
                 '--exe', test.pli_filename, '--no-timing', '+define+NBA_EVENT_CAPTURE_KNOWN',
                 '-CFLAGS', '-std=c++14'
             ])

test.execute()
test.file_grep(test.run_log_filename, r'NBA event capture checks: (\d+)', 4)
test.file_grep_not(test.run_log_filename, r'%Error|%Warning')
test.passes()
