#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import os

import vltest_bootstrap

test.scenarios('vlt', 'iv')

base_dir = test.obj_dir
base_iv_flags = [flag for flag in test.iv_flags if not flag.startswith('-o')]
for case in range(6):
    test.obj_dir = base_dir + '/case' + str(case)
    test.mkdir_ok(test.obj_dir)
    test.iv_flags = base_iv_flags + ['-o' + test.obj_dir + '/simiv']
    flags = ['--binary', '--top-module', 't', '--Mdir', test.obj_dir, '-j', '1']
    flags += ['-MAKEFLAGS', 'VM_PARALLEL_BUILDS=0']
    if case not in (2, 5):
        flags += ['--no-timing']
    test.compile(
        make_top_shell=False,
        make_main=False,
        v_flags2=['+define+FINISH_CASE=' + str(case)],
        verilator_flags2=flags,
    )
    log = test.obj_dir + '/run.log'
    golden = test.golden_filename.removesuffix('.out') + '_case' + str(case) + '.out'
    test.execute(
        executable=test.obj_dir + '/' + test.vm_prefix,
        logfile=log,
        check_finished=True,
        iv_run_flags=['-N'],
    )
    test.file_grep_not(log, r'UNREACHABLE|%Error|ERROR:')
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
    # Generate only new gold from the Icarus reference. Do not bless candidate
    # output merely because its native process returns zero.
    if test.iv and 'HARNESS_UPDATE_GOLDEN' in os.environ:
        test.copy_if_golden(log, golden)
    test.files_identical(log, golden, is_logfile=True)

test.obj_dir = base_dir
test.passes()
