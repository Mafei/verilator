#!/usr/bin/env python3
# DESCRIPTION: Verilator: Primary API initialization with four-state storage
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
base_dir = test.obj_dir
base_v_flags = [flag for flag in test.v_flags if 'TEST_DUMPFILE' not in flag]
for profile, options, api in (('default', [], True), ('on', ['--fourstate-api'], True),
                              ('off', ['--no-fourstate-api'], False)):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    flags = [
        '--binary', '--fourstate', '--trace', '--trace-depth', '2', '--debug-check', '-Wno-FUTURE',
        '--top-module', 't', '--Mdir', test.obj_dir, '-j', '1', '-MAKEFLAGS',
        'VM_PARALLEL_BUILDS=1', '--output-split', '10000', '--output-split-cfuncs', '100', *options
    ]
    test.compile(
        make_top_shell=False,
        make_main=False,
        v_flags2=['+define+EXPECT_PRIMARY_API'] if api else [],
        verilator_flags2=flags,
    )
    log = test.obj_dir + '/run.log'
    test.execute(
        executable=test.obj_dir + '/' + test.vm_prefix,
        logfile=log,
        check_finished=True,
    )
    test.file_grep(log, r'^API initializer checks: (\d+)$', 102)
    test.file_grep_count(log, r'^API initializer checks:', 1)
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
    test.file_grep_not(log, r'%Error|ERROR:|Aborting')
    expected = {
        't.implicit_scalar': [(0, '0' if api else 'z')],
        't.variable_scalar': [(0, '0' if api else 'x')],
        't.primary_variable7': [(0, 'x' * 7)],
        't.primary_wire33': [(0, 'z' * 33)],
        't.primary_explicit65': [(0, 'x' * 65)],
        't.internal_variable7': [(0, 'x' * 7)],
        't.internal_wire33': [(0, 'z' * 33)],
        't.child_variable65': [(0, 'x' * 65)],
        't.child_wire95': [(0, 'z' * 95)],
        't.checks': [(0, '0' * 32), (1000, format(34, '032b')), (2000, format(68, '032b')),
                     (3000, format(102, '032b'))],
    }
    for width in (7, 33, 65, 95, 129):
        for kind in ('implicit', 'typed', 'wire', 'variable', 'ascending'):
            state = '0' if api else ('x' if kind == 'variable' else 'z')
            expected['t.' + kind + str(width)] = [(0, state * width)]
    check_trace(test, expected, {name: len(values[0][1]) for name, values in expected.items()})

test.obj_dir = base_dir
test.passes()
