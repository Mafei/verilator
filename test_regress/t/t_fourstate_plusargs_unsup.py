#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')

base_dir = test.obj_dir
for case in range(2):
    test.obj_dir = base_dir + '/case' + str(case)
    test.mkdir_ok(test.obj_dir)
    flags = ['--fourstate', '-Wno-FUTURE', '--top-module', 't', '--Mdir', test.obj_dir]
    defines = ['+define+PLUSARGS_UNSUP_SLICE'] if case == 0 else []
    golden = test.golden_filename.removesuffix('.out') + '_case' + str(case) + '.out'
    test.lint(verilator_flags2=flags,
              v_flags2=defines,
              fails=True,
              expect_filename=golden)

# This inherited two-state selected-output control has no Icarus 12 gold.
# Its four-state index must not be mistaken for four-state output storage.
test.obj_dir = base_dir + '/case2'
test.mkdir_ok(test.obj_dir)
test.compile(
    make_top_shell=False,
    make_main=False,
    v_flags2=['+define+PLUSARGS_LEGACY_BITS'],
    verilator_flags2=[
        '--binary', '--fourstate', '-Wno-FUTURE', '--top-module', 't',
        '--Mdir', test.obj_dir, '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=0',
    ],
)
log = test.obj_dir + '/run.log'
test.execute(executable=test.obj_dir + '/' + test.vm_prefix,
             logfile=log,
             check_finished=True,
             all_run_flags=['+W7=ff', '+quiet'])
test.file_grep_not(log, r'UNREACHABLE|%Error|ERROR:')
test.file_grep_count(log, r'^LEGACY_BITS checks=4$', 1)
test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)

test.obj_dir = base_dir
test.passes()
