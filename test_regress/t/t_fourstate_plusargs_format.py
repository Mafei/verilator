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
test.compile(
    make_top_shell=False,
    make_main=False,
    verilator_flags2=[
        '--binary', '--fourstate', '-Wno-FUTURE', '--top-module', 't',
        '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=0',
    ],
)
run_flags = ['+INT=1234', '+HNT=99', '+KNT=777']
log = test.obj_dir + '/run.log'
if test.iv:
    test.run(cmd=['vvp', '-N', test.obj_dir + '/simiv', *run_flags],
             logfile=log,
             check_finished=True)
else:
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix,
                 logfile=log,
                 check_finished=True,
                 all_run_flags=run_flags)
test.file_grep_not(log, r'UNREACHABLE|%Error|ERROR:|WARNING:')
test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
if test.iv and 'HARNESS_UPDATE_GOLDEN' in os.environ:
    test.copy_if_golden(log, test.golden_filename)
test.files_identical(log, test.golden_filename, is_logfile=True)
test.passes()
