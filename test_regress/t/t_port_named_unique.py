#!/usr/bin/env python3
# DESCRIPTION: Verilator: One direct named OUTPUT alias per internal wire
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
checks = (
    (0, 'named33', '000000000000000000000000000000000'),
    (0, 'positional65', '11111111111111111111111111111111111111111111111111111111111111111'),
    (0, 'star33', '111111111111111111111111111111111'),
    (1, 'named33', '111111111111111111111111111111111'),
    (1, 'positional65', '00000000000000000000000000000000000000000000000000000000000000000'),
    (1, 'star33', '000000000000000000000000000000000'),
    (2, 'named33', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    (2, 'positional65', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    (2, 'star33', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    (3, 'named33', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    (3, 'positional65', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    (3, 'star33', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    (4, 'named33', '10xz01zx10xz01zx10xz01zx10xz01zx0'),
    (4, 'positional65', 'zx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz10zx01xz101'),
    (4, 'star33', '01zx10xz01zx10xz01zx10xz01zx10xz1'),
    (4, 'named33_msb35', '1'),
    (4, 'named33_lsb3', '0'),
    (4, 'positional65_msb67', 'z'),
    (4, 'positional65_lsb3', '1'),
)
expected = [
    'NAMED_UNIQUE_CHECK n=' + str(i) + ' phase=' + str(phase) + ' label=' + label + ' got=' + value
    for i, (phase, label, value) in enumerate(checks, 1)
]
expected += ['NAMED_UNIQUE checks=19', '*-* All Finished *-*']
test.compile(make_top_shell=False,
             make_main=False,
             verilator_flags2=[
                 '--binary', '--fourstate', '-Wno-FUTURE', '--debug-check', '--top-module', 't',
                 '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1'
             ])
test.file_grep_not(test.obj_dir + '/vlt_compile.log', r'%Warning-|%Error|fatal error:|warning:')
log = test.obj_dir + '/run.log'
test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
test.file_grep_not(log, r'%Error|ERROR:|%Fatal|FAILED|Assertion|Segmentation fault|Internal Error')
owned = [
    line for line in test.file_contents(log).splitlines()
    if line.startswith('NAMED_UNIQUE') or line == '*-* All Finished *-*'
]
if owned != expected:
    test.error('Missing, duplicate, reordered or incorrect unique OUTPUT alias state')
test.file_grep_count(log, r'^NAMED_UNIQUE_CHECK ', 19)
test.file_grep_count(log, r'^NAMED_UNIQUE checks=19$', 1)
test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
test.passes()
