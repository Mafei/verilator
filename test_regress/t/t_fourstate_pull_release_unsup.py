#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import os
import shutil

import vltest_bootstrap

test.scenarios('vlt_all')

for number in range(1, 13):
    log = f'{test.obj_dir}/case_{number}.log'
    golden = test.golden_filename.removesuffix('.out') + f'_{number}.out'
    test.compile(verilator_flags2=['--fourstate', '--timing', '-Wno-FUTURE', '--top-module', 't',
                                  f'-DPULL_CASE_{number}'],
                 fails=True)
    shutil.copyfile(test.obj_dir + '/vlt_compile.log', log)
    test.file_grep_not(log, r'Internal Error|syntax error')
    test.file_grep(log, r'Unsupported: Driven tri0/tri1 net')
    if not os.path.exists(golden):
        test.copy_if_golden(log, golden)
    test.files_identical(log, golden, is_logfile=True)
test.passes()
