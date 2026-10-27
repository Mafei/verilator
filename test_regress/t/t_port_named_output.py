#!/usr/bin/env python3
# DESCRIPTION: Verilator: Distinct direct named OUTPUT header aliases
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')

labels = ('scalar_named', 'scalar_positional', 'packed13_named', 'packed13_positional',
          'packed31_named', 'internal_left')
# Independent literal oracle: retain both fanout receivers and exact X/Z order.
values = (
    ('00', '11', '00000000000000000000000000', '11111111111111111111111111',
     '00000000000000000000000000000000000000000000000000000000000000', '1'),
    ('11', '00', '11111111111111111111111111', '00000000000000000000000000',
     '11111111111111111111111111111111111111111111111111111111111111', '1'),
    ('xx', 'zz', 'xxxxxxxxxxxxxxxxxxxxxxxxxx', 'zzzzzzzzzzzzzzzzzzzzzzzzzz',
     'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', '1'),
    ('zz', 'xx', 'zzzzzzzzzzzzzzzzzzzzzzzzzz', 'xxxxxxxxxxxxxxxxxxxxxxxxxx',
     'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz', '1'),
    ('11', '00', '10xz01zx10xz010xz01zx10xz0', 'zx10xz01zx10zzx10xz01zx10z',
     '10xz01zx10xz010xz01zx10xz010xz010xz01zx10xz010xz01zx10xz010xz0', '1'),
)
expected = []
for phase, row in enumerate(values):
    for label, value in zip(labels, row):
        expected.append('NAMED_OUTPUT_CHECK n=' + str(len(expected) + 1) + ' phase=' + str(phase) +
                        ' label=' + label + ' got=' + value)
expected += ['NAMED_OUTPUT checks=30', '*-* All Finished *-*']

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
    if line.startswith('NAMED_OUTPUT') or line == '*-* All Finished *-*'
]
if owned != expected:
    test.error('Missing, duplicate, reordered or incorrect direct named OUTPUT result')
test.file_grep_count(log, r'^NAMED_OUTPUT_CHECK ', 30)
test.file_grep_count(log, r'^NAMED_OUTPUT checks=30$', 1)
test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
test.passes()
