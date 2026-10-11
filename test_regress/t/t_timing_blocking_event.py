#!/usr/bin/env python3
# DESCRIPTION: Verilator: Blocking intra-assignment event capture
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
fourstate = test.name == 't_fourstate_blocking_event'
flags = ['--binary', '--trace', '--debug-check']
if fourstate:
    flags += ['--fourstate', '-Wno-FUTURE']
test.compile(verilator_flags2=flags)
test.execute()
test.file_grep(test.run_log_filename, r'^Blocking event checks: (\d+)$', 112)

cycles = '01xz' if fourstate else '0110'


def pattern(width, seed):
    return ''.join(cycles[(width - 1 - index + seed) % 4] for index in range(width))


expected = {}
widths = {}
for width in [7, 31, 65, 95]:
    stem = f't.w{width}.'
    values = {
        'whole_view': (width, [(0, '0' * width), (3, pattern(width, 0))]),
        'bank1_view': (width + 2, [(0, '0' * (width + 2))]),
        'bank2_view': (width + 2, [(0, '0' * (width + 2)), (6, '0' + pattern(width, 1) + '0')]),
        'delayed_view': (width, [(0, '0' * width), (9, pattern(width, 2))]),
        'queued1_view': (width, [(0, '0' * width), (11, pattern(width, 1))]),
        'queued2_view': (width, [(0, '0' * width), (11, pattern(width, 2))]),
        'queued3_view': (width, [(0, '0' * width), (11, pattern(width, 3))]),
    }
    for name, (bits, history) in values.items():
        expected[stem + name] = history
        widths[stem + name] = bits
check_trace(test, expected, widths)
test.passes()
