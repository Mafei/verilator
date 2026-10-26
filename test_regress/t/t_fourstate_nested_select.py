#!/usr/bin/env python3
# DESCRIPTION: Verilator: Packed element offsets preserve bounds before nested reads
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
    '--binary', '--fourstate', '-Wno-FUTURE', '--trace', '--debug-check', '--build-jobs', '1'
],
             make_flags=['-j1'])
test.execute()
test.file_grep(test.run_log_filename, r'^Nested selection checks: (\d+)$', 34)
test.file_grep_count(test.run_log_filename, r'^NESTED SELECT ', 8)
palette7 = [('0xz1010', 'z10x011'), ('1zx0101', '10z1100')]
palette33 = [('0' + '10zx' * 8, 'x' + '00z1' * 8), ('1' + '01xz' * 8, 'z' + '1100' * 8)]
widths = {'t.r7': 1, 't.r33': 1, 't.w7': 7, 't.w33': 33}
expected = {name: [(0, '0' * width)] for name, width in widths.items()}
for step in range(8):
    row7 = [0, 1, 2, 613566756, 613566757, 2**32 - 1, None, 0][step]
    row33 = [0, 1, 2, 130150524, 130150525, 2**32 - 1, None, 0][step]
    row95 = [0, 1, 2, 2**64, 2**64 + 1, 2**95 - 1, None, 1][step]
    values = []
    for name, row, bit in [('r7', row7, 4), ('r33', row33, 4), ('w7', row95, None),
                           ('w33', row95, None)]:
        palette = palette7 if name.endswith('7') else palette33
        value = palette[step % 2][row] if row in (0, 1) else 'x' * len(palette[0][0])
        if bit is not None:
            value = value[-1 - bit]
        values.append((name, value))
        key = 't.' + name
        if expected[key][-1][1] != value:
            expected[key].append((2 * step + 1, value))
    fields = ''.join(f' {name}={value}' for name, value in values)
    test.file_grep(test.run_log_filename, f'^NESTED SELECT step={step} t={2 * step + 2}{fields}$')
check_trace(test, expected, widths)
test.passes()
