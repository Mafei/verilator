#!/usr/bin/env python3
# DESCRIPTION: Verilator: Clipped event NBA values, targets and scheduling
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
fourstate = test.name == 't_fourstate_nba_partselect_clip'
flags = ['--binary', '--trace', '--sched-zero-delay', '--debug-check', '--build-jobs', '1']
if fourstate:
    flags += ['--fourstate', '-Wno-FUTURE']
test.compile(verilator_flags2=flags, make_flags=['-j1'])
test.execute()
test.file_grep(test.run_log_filename, r'^Clipped NBA checks: (\d+)$', 576)
test.file_grep_count(test.run_log_filename, r'^CLIP STROBE ', 72)

expected = {}
widths = {}
pattern = ''.join(('01xz'[bit % 4] if fourstate else str(int(bit % 3 == 1))) for bit in range(97))
for width in (4, 63, 65, 95):
    names = [f't.w{width}.bank{index}_view' for index in (0, 1)]
    for name in names:
        expected[name] = []
        widths[name] = width
    for roundno in range(2):
        for kind in range(9):
            step = 9 * roundno + kind
            initial = [str(int((bit + roundno + kind) % 3 == 1)) for bit in range(width)]
            other = ['1' if value == '0' else '0' for value in initial]
            low = '1z' if fourstate else '01'
            high = 'x1' if fourstate else '10'
            valid = 'zx' if fourstate else '01'
            lsb, bits = [(-1, low), (width - 1, high), (-2, '11'), (width, '11'),
                         (-1, pattern[:width + 2]), (1, valid), (-1, pattern[:6]),
                         (31 if width > 4 else 1, pattern[:33]),
                         (width + 1, pattern[:2])][kind]
            # Character-vector insertion is independent of the compiler's bulk bit helpers.
            final = initial[:]
            for source_bit, value in enumerate(bits):
                if 0 <= lsb + source_bit < width:
                    final[lsb + source_bit] = value
            for name, values in zip(names, (initial, other)):
                value = ''.join(reversed(values))
                if not expected[name] or expected[name][-1][1] != value:
                    expected[name].append((3 * step, value))
            value = ''.join(reversed(final))
            if expected[names[0]][-1][1] != value:
                expected[names[0]].append((3 * step + 1, value))
            other_value = ''.join(reversed(other))
            test.file_grep(
                test.run_log_filename,
                f'^CLIP STROBE width={width} round={roundno} case={kind} t={3 * step + 1}'
                f' bank0={value} bank1={other_value}$')
check_trace(test, expected, widths)
test.passes()
