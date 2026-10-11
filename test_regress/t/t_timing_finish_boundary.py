#!/usr/bin/env python3
# DESCRIPTION: Verilator: Immediate finish across NBA and inactive boundaries
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import os

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
base_dir = test.obj_dir
base_v_flags = [flag for flag in test.v_flags if 'TEST_DUMPFILE' not in flag]
for case in range(10):
    test.obj_dir = base_dir + '/case' + str(case)
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    flags = ['--binary', '--trace', '--sched-zero-delay', '--top-module', 't']
    flags += ['--Mdir', test.obj_dir, '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=0']
    test.compile(
        make_top_shell=False,
        make_main=False,
        v_flags2=['+define+FINISH_BOUNDARY_CASE=' + str(case)],
        verilator_flags2=flags,
    )
    log = test.obj_dir + '/run.log'
    golden = 't/t_timing_finish_boundary_case' + str(case) + '.out'
    test.execute(
        executable=test.obj_dir + '/' + test.vm_prefix,
        logfile=log,
        check_finished=True,
    )
    test.file_grep_not(log, r'BAD|%Error|ERROR:')
    test.file_grep_count(log, r'^FINAL case=', 1)
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
    test.file_grep_count(log, r'^BEFORE case=', 0 if case == 8 else 1)
    test.file_grep_count(log, r'^GOOD postponed case=', 1 if case in (2, 8) else 0)
    test.file_grep_count(log, r'^CONTROL case=', 1 if case == 8 else 0)
    test.file_grep_count(log, r'^NORMAL noninline value=', 1 if case == 8 else 0)
    test.file_grep_count(log, r'^NORMAL ref value=', 1 if case == 8 else 0)
    test.file_grep_count(log, r'^NORMAL ref owner target=', 1 if case == 8 else 0)
    expected = {
        't.q': [(0, '0')],
        't.word7': [(0, '0' * 7)],
        't.word65': [(0, '0' * 65)],
        't.tail': [(0, '0' * 32)],
        't.inactive_done': [(0, '0' * 32)],
        't.function_result': [(0, format(41, '032b'))],
    }
    if case in (2, 8):
        expected['t.q'].append((1, '1'))
        expected['t.word7'].append((1, '0010100'))
        expected['t.word65'].append((1, format(20 << 33, '065b')))
    check_trace(test, expected, {name: len(values[0][1]) for name, values in expected.items()})
    # Generate new gold only from an actual candidate run whose SV self-checks,
    # exact output counts, forbidden-tail checks and complete wave checks passed.
    # Existing finish9 gold is never modified by this driver.
    if test.vlt and not test.errors and not test.errors_keep_going:
        if 'HARNESS_UPDATE_GOLDEN' in os.environ:
            test.copy_if_golden(log, golden)
    if not test.errors and not test.errors_keep_going:
        test.files_identical(log, golden, is_logfile=True)

test.obj_dir = base_dir
test.passes()
