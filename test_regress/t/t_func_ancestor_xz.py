#!/usr/bin/env python3
# DESCRIPTION: Verilator: Four-state ancestor task context regression
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')

# Predeclared literals are independent of the fixture's task expressions.
checks = (
    ('a_first', '10xx01xx'),
    ('aa_first', '01xx10xx'),
    ('b_first', 'zx10x1z0'),
    ('a_nearest_first', '10xz10xz'),
    ('aa_nearest_first', '01zx01zx'),
    ('a_first_state', '10xz01zx'),
    ('aa_first_state', '01zx10xz'),
    ('b_first_state', 'x1z0zx10'),
    ('a_nearest_first_state', '10xz01zx'),
    ('aa_nearest_first_state', '01zx10xz'),
    ('a_first_calls', '00000001'),
    ('aa_first_calls', '00000001'),
    ('b_first_calls', '00000001'),
    ('a_nearest_first_calls', '00000001'),
    ('aa_nearest_first_calls', '00000001'),
    ('a_second', '01xx10xx'),
    ('aa_second', '10xx01xx'),
    ('b_second', 'xx01x0x1'),
    ('a_nearest_second', '01xx01xx'),
    ('aa_nearest_second', '10xx10xx'),
    ('a_second_state', '01xx10xx'),
    ('aa_second_state', '10xx01xx'),
    ('b_second_state', 'x0x1xx01'),
    ('a_nearest_second_state', '01xx10xx'),
    ('aa_nearest_second_state', '10xx01xx'),
    ('a_second_calls', '00000010'),
    ('aa_second_calls', '00000010'),
    ('b_second_calls', '00000010'),
    ('a_nearest_second_calls', '00000010'),
    ('aa_nearest_second_calls', '00000010'),
)
flags = ['--binary', '--debug-check', '--top-module', 't', '--Mdir', test.obj_dir]
flags += ['-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1', '--fourstate', '-Wno-FUTURE']
test.compile(make_top_shell=False, make_main=False, verilator_flags2=flags)
test.file_grep_not(test.obj_dir + '/vlt_compile.log', r'%Warning-|%Error|fatal error:|warning:')
log = test.obj_dir + '/run.log'
test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
test.file_grep_not(log, r'%Error|ERROR:|%Fatal|FAILED')
expected = [
    'ANCESTOR_XZ_CHECK n=' + str(index) + ' label=' + label + ' got=' + value
    for index, (label, value) in enumerate(checks, 1)
]
expected += ['ANCESTOR_XZ checks=30', '*-* All Finished *-*']
owned = [line for line in test.file_contents(log).splitlines()
         if line.startswith('ANCESTOR_XZ') or line == '*-* All Finished *-*']
if owned != expected:
    test.error('Missing, duplicate, reordered or incorrect ancestor XZ output')
test.file_grep_count(log, r'^ANCESTOR_XZ_CHECK ', 30)
test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
test.passes()
