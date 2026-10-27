#!/usr/bin/env python3
# DESCRIPTION: Verilator: Packed word slices retain full index domains
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
test.file_grep(test.run_log_filename, r'^Packed slice checks: (\d+)$', 98)
test.file_grep_count(test.run_log_filename, r'^PACKED SLICE ', 24)

words7 = ['10xz001', '0z110x1', 'z0011x0', '011z0x1', 'x1010z0', '110x1z0']
words33 = [
    '1' + '01xz' * 8, '0' + 'z1x0' * 8, 'z' + '10zx' * 8, 'x' + '0z11' * 8, '1' + 'zx00' * 8,
    '0' + 'x1z1' * 8
]
widths = {'t.r7': 14, 't.m7': 14, 't.r33': 66, 't.m33': 66}
expected = {name: [(0, '0' * width)] for name, width in widths.items()}
for step in range(24):
    domain, kind = divmod(step, 4)
    phase = step % 2
    outer = (domain + kind) % 2
    if kind == 0:
        bases = [1, 4, 4, 4]
    elif kind == 1:
        bases = [2, 6, 5, 6] if domain % 2 else [-1, 3, 2, 3]
    elif kind == 2:
        # Python integers retain the entire original signed/unsigned index value.
        large = [-2**31, 2**32 - 1, 2**32, 2**32 + 1, -2**64, 2**64 + 4][domain]
        bases = [large] * 4
    else:
        bases = [None] * 4
    values = []
    for name, base in zip(('r7', 'm7', 'r33', 'm33'), bases):
        palette = words7 if name.endswith('7') else words33
        element_width = 7 if name.endswith('7') else 33
        bank = (phase + outer) % 2 if name.startswith('m') else phase
        low = 0 if name == 'r7' else 3
        # Map declared word numbers to literal strings. No flattened multiply,
        # index narrowing, modulo addressing, clipping helper or simulator values.
        declared = {low + word: palette[3 * bank + word] for word in range(3)}
        if base is None:
            selected = [None, None]
        elif name.startswith('r'):
            selected = [base + 1, base]
        elif name == 'm7':
            selected = [base, base - 1]
        else:
            selected = [base - 1, base]
        value = ''.join(declared.get(word, 'x' * element_width) for word in selected)
        values.append((name, value))
        signal = f't.{name}'
        if expected[signal][-1][1] != value:
            expected[signal].append((2 * step + 1, value))
    fields = ''.join(f' {name}={value}' for name, value in values)
    test.file_grep(
        test.run_log_filename,
        f'^PACKED SLICE step={step} domain={domain} kind={kind} t={2 * step + 2}{fields}$')
check_trace(test, expected, widths)
test.passes()
