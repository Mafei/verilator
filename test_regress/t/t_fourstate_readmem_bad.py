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

test.scenarios('vlt_all')

data = {
    0: '10_2\n',
    1: '12g\n',
    2: '@1x 1x\n',
    3: '@100000000 1x\n',
    4: '@5 1x\n',
    5: '@-1 1x\n',
    7: '1x z5 az 3c e5\n',
    8: '1x z5\n',
    9: 'X1_aZ\n',
    10: 'x1_1001_0xz\n',
}
for number, contents in data.items():
    with open(f'{test.obj_dir}/bad_{number}.mem', 'w', encoding='ascii') as stream:
        stream.write('// SPDX-License-Identifier: CC0-1.0\n' + contents)

errors = {
    0: '$readmemb invalid data digit',
    1: '$readmemh invalid data digit',
    2: '$readmem invalid address digit (X/Z and signed text are not allowed)',
    3: '$readmem address exceeds the supported 32-bit declaration domain',
    4: '$readmem address outside the requested range',
    5: '$readmem invalid address digit (X/Z and signed text are not allowed)',
}

test.compile(verilator_flags2=['--binary', '--fourstate', '-Wno-FUTURE'])
for number in range(11):
    log = f'{test.obj_dir}/case_{number}.log'
    golden = test.golden_filename.removesuffix('.out') + f'_{number}.out'
    test.execute(all_run_flags=[f'+CASE={number}'],
                 logfile=log,
                 fails=number < 6,
                 check_finished=number >= 6,
                 expect_filename=golden)
    test.file_grep_not(log, r'Internal Error')
    if number < 6:
        test.file_grep_not(log, r'Malformed readmem input unexpectedly returned')
        test.file_grep(log, re.escape(errors[number]))
    if number >= 6:
        test.file_grep(log, r'Readmem diagnostic checks: (\d+)', 156 if number == 6 else 12)
test.passes()
