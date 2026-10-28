#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
base_dir = test.obj_dir
base_flags = test.verilator_flags[:]
for profile, options in (('two', []), ('four', ['--fourstate', '-Wno-FUTURE'])):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.verilator_flags = base_flags[:]
    test.compile(
        make_top_shell=False,
        make_main=False,
        verilator_flags2=[
            '--binary', '--debug-check', '--top-module', 't', '--Mdir', test.obj_dir, '-j', '1',
            '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1', *options
        ],
    )
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep(log, r'Two-state queue lambda checks: (\d+)', 64)
    test.file_grep_not(log, r'%Error|ERROR:|Aborting')
test.obj_dir = base_dir
test.verilator_flags = base_flags
test.passes()
