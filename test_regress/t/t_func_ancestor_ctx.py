#!/usr/bin/env python3
# DESCRIPTION: Verilator: Ancestor context prototype regression (UNEXECUTED)
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')

# Identical source/inputs/oracle in both profiles. These 15 checks use known bits.
base_dir = test.obj_dir
base_v_flags = test.v_flags.copy()
checks = (
    ('a_first', 'a1'),
    ('a_second', 'a2'),
    ('aa_first', 'a1'),
    ('aa_second', 'a2'),
    ('b_first', 'b1'),
    ('b_second', 'b2'),
    ('a_nearest_first', 'c1'),
    ('a_nearest_second', 'c2'),
    ('aa_nearest_first', 'c1'),
    ('aa_nearest_second', 'c2'),
    ('a_state', '2'),
    ('aa_independent_state', '2'),
    ('b_state', '2'),
    ('a_nearest_state', '2'),
    ('aa_nearest_state', '2'),
)
for profile in ('two_state', 'four_state'):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    flags = ['--binary', '--debug-check', '--top-module', 't', '--Mdir', test.obj_dir]
    flags += ['-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1']
    if profile == 'four_state':
        flags += ['--fourstate', '-Wno-FUTURE']
    test.compile(make_top_shell=False, make_main=False, verilator_flags2=flags)
    test.file_grep_not(test.obj_dir + '/vlt_compile.log', r'%Warning-|%Error|fatal error:|warning:')
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep_not(log, r'%Error|ERROR:|%Fatal|FAILED')
    expected = [
        'ANCESTOR_CHECK n=' + str(index) + ' label=' + label + ' got=' + value
        for index, (label, value) in enumerate(checks, 1)
    ]
    expected += ['ANCESTOR_STATE checks=15', '*-* All Finished *-*']
    owned = [line for line in test.file_contents(log).splitlines()
             if line.startswith('ANCESTOR_') or line == '*-* All Finished *-*']
    if owned != expected:
        test.error('Missing, duplicate, reordered or incorrect ancestor context output: ' + profile)
    test.file_grep_count(log, r'^ANCESTOR_CHECK ', 15)
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)

test.obj_dir = base_dir
test.v_flags = base_v_flags
test.passes()
