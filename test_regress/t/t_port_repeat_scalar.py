#!/usr/bin/env python3
# DESCRIPTION: Verilator: Repeated scalar OUTPUT wire ports
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')

# Independent literal protocol; preserve the raw simulator footer in each run.log.
checks = (
    ('p0_a_left', '0'),
    ('p0_a_right', '0'),
    ('p0_b_left', '1'),
    ('p0_b_right', '1'),
    ('p0_unique', '0'),
    ('p1_a_left', '1'),
    ('p1_a_right', '1'),
    ('p1_b_left', '0'),
    ('p1_b_right', '0'),
    ('p1_unique', '1'),
    ('p2_a_left', 'x'),
    ('p2_a_right', 'x'),
    ('p2_b_left', 'z'),
    ('p2_b_right', 'z'),
    ('p2_unique', 'x'),
    ('p3_a_left', 'z'),
    ('p3_a_right', 'z'),
    ('p3_b_left', 'x'),
    ('p3_b_right', 'x'),
    ('p3_unique', 'z'),
)
base_dir = test.obj_dir
base_v_flags = test.v_flags.copy()
for profile, defines in (('implicit', []), ('explicit', ['+define+EXPLICIT_SCALAR'])):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    flags = [
        '--binary', '--fourstate', '--debug-check', '-Wno-FUTURE', '--top-module', 't', '--Mdir',
        test.obj_dir, '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1'
    ]
    test.compile(make_top_shell=False, make_main=False, v_flags2=defines, verilator_flags2=flags)
    test.file_grep_not(test.obj_dir + '/vlt_compile.log',
                       r'%Warning-|%Error|fatal error:|warning:')
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep_not(log,
                       r'%Error|ERROR:|%Fatal|FAILED|Assertion|Segmentation fault|Internal Error')
    expected = [
        'PORT_REPEAT_SCALAR_CHECK n=' + str(i) + ' label=' + label + ' got=' + value
        for i, (label, value) in enumerate(checks, 1)
    ]
    expected += ['PORT_REPEAT_SCALAR checks=20', '*-* All Finished *-*']
    owned = [
        line for line in test.file_contents(log).splitlines()
        if line.startswith('PORT_REPEAT_SCALAR') or line == '*-* All Finished *-*'
    ]
    if owned != expected:
        test.error('Missing, duplicate, reordered or incorrect scalar OUTPUT state: ' + profile)
    test.file_grep_count(log, r'^PORT_REPEAT_SCALAR_CHECK ', 20)
    test.file_grep_count(log, r'^PORT_REPEAT_SCALAR checks=20$', 1)
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
test.obj_dir = base_dir
test.v_flags = base_v_flags
test.passes()
