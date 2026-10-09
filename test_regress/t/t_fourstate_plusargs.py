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
        '--binary', '--fourstate', '-Wno-FUTURE', '-Wno-ASCRANGE', '--top-module', 't',
        '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=0',
    ],
)
run_flags = [
    '+STOP_AT=2', '+STOP_ENABLE=0',
    '+W7=ff', '+W31=ffffffff', '+W33=3ffffffff',
    '+W65=3ffffffffffffffff', '+W95=ffffffffffffffffffffffff',
    '+NEG65=-3', '+NEG95=-300000000000', '+DEC95=39614081257132168796771975167',
    '+NEG_CARRY=-4294967295', '+NEG_ZERO=-4294967296',
    '+HX33=x1', '+HZ65=z1', '+HB7=10xzz01', '+HO31=x1', '+HX95=12xzz',
    '+DX95=x', '+DZ95=z', '+XX7=xz',
]
log = test.obj_dir + '/run.log'
if test.iv:
    # The harness's execute() puts all_run_flags before the vvp input file.
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
# Only the independent Icarus reference may create this semantic golden.
if test.iv and 'HARNESS_UPDATE_GOLDEN' in os.environ:
    test.copy_if_golden(log, test.golden_filename)
test.files_identical(log, test.golden_filename, is_logfile=True)
test.passes()
