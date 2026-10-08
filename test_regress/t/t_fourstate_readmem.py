#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import re

import vltest_bootstrap

test.scenarios('simulator')


def encode(value, binary):
    return value if binary else format(int(value, 2), 'x')


widths = (1, 7, 8, 9, 16, 17, 32, 33, 64, 65, 95, 128, 176)
for width in widths:
    for binary in (False, True):
        suffix = ('b' if binary else 'h') + str(width) + '.mem'
        digits = width if binary else (width + 3) // 4
        known = ''.join('1' if bit % 3 == 1 else '0' for bit in reversed(range(width)))
        complement = ''.join('1' if bit == '0' else '0' for bit in known)
        mixed = ''.join(('xz10' if binary else 'xZ5a')[bit % 4] for bit in reversed(range(digits)))
        other = ''.join(('zX01' if binary else 'Zxa5')[bit % 4] for bit in reversed(range(digits)))
        # Use one token per destination width; positive tests avoid excess-digit
        # warnings. Whitespace, case, comments and underscores remain deliberate.
        contents = {
            'mixed':
            '0 /* block\ncomment */ ' + encode(known, binary) + '\n' + '_'.join(mixed) +
            ' // line comment\n' + '_'.join(other) + '\n',
            'known':
            encode(complement, binary) + '\n' + encode(known, binary) + '\n',
            'sparse':
            '@1 ' + mixed + '\n@4 ' + other + '\n',
            'short':
            '1',
            'short_x':
            'X',
            'short_z':
            'z',
        }
        for stem, data in contents.items():
            with open(test.obj_dir + '/' + stem + '_' + suffix, 'w', encoding='ascii') as stream:
                stream.write('// SPDX-License-Identifier: CC0-1.0\n' + data)

test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename)
test.file_grep(test.run_log_filename, r'Readmem width checks: (\d+)', 3510)
test.file_grep(test.run_log_filename, r'Readmem observer checks: (\d+)', 10)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')

# Parse scalar mirrors directly. Preserve distinct x/z characters instead of
# passing through a formatter that can normalize unknown states.
codes = {}
histories = {}
with open(test.trace_filename, encoding='ascii') as stream:
    for line in stream:
        line = line.lstrip()
        declaration = re.match(r'\$var \w+ 8 (\S+) (probe_\w+) ', line)
        if declaration:
            codes[declaration[1]] = declaration[2]
            histories[declaration[2]] = []
        value = re.match(r'b([01xzXZ]+) (\S+)', line)
        if value and value[2] in codes:
            bits = value[1].lower()
            bits = bits.rjust(8, bits[0] if bits[0] in 'xz' else '0')
            history = histories[codes[value[2]]]
            if not history or history[-1] != bits:
                history.append(bits)
expected = {
    'probe_h': ['xxxxxxxx', 'zzzzxxxx', '10010010', '0000xxxx'],
    'probe_b': ['xxxxxxxx', '01zx01zx', '10010010', '0000000x'],
    'probe_h_z': ['xxxxxxxx', 'xxxxzzzz', '00000001', '0000zzzz'],
    'probe_b_z': ['xxxxxxxx', '10xz10xz', '00000001', '0000000z'],
}
if histories != expected:
    test.error(f'Readmem scalar VCD mismatch: {histories}, expected {expected}')
print('Readmem scalar VCD checks: 4')
test.passes()
