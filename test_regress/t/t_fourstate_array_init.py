#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
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
for width in (7, 33, 65):
    test.obj_dir = base_dir + '/width' + str(width)
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    flags = ['--binary', '--fourstate', '-Wno-FUTURE', '--trace', '--top-module', 't']
    flags += ['--Mdir', test.obj_dir, '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1']
    flags += ['--output-split', '10000', '--output-split-cfuncs', '50']
    test.compile(
        make_top_shell=False,
        make_main=False,
        v_flags2=['+define+ARRAY_INIT_WIDTH=' + str(width)],
        verilator_flags2=flags,
    )
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep_not(log, r'%Error|ERROR:|%Fatal')
    test.file_grep_count(log, r'^ARRAY_INIT_FINAL width=' + str(width) + ' ', 1)
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
    expected = {
        't.bank' + str(index): [(0, format(value, '0' + str(width) + 'b'))]
        for index, value in ((1, 0x11), (2, 0x22), (3, 0x33))
    }
    check_trace(test, expected, {name: width for name in expected})

test.obj_dir = base_dir
test.passes()
