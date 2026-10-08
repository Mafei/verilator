#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import os
import re
import shutil

import vltest_bootstrap

test.scenarios('vlt_all')

# Goldens are generated from real diagnostics after compilation. MOS switches,
# conditional-strength contributions and complex live procedural RHS stay explicit.
reasons = {
    1: 'Tristate buffer with --fourstate: explicit drive strength.',
    2: 'Tristate buffer with --fourstate: drive delay.',
    3: 'Tristate buffer with --fourstate: MOS transistor primitive.',
    4: 'Tristate buffer with --fourstate: MOS transistor primitive.',
    5: 'with --fourstate: tristate primitive contribution.',
    6: 'with --fourstate: tristate primitive contribution.',
    7: 'Procedural continuous assignment with --fourstate: compound RHS requiring live expression lowering.',
    8: 'Procedural deassign with --fourstate: nonlocal or nonpacked variable.',
    9: 'Procedural deassign with --fourstate: partial or hierarchical target.',
    10: 'Procedural deassign with --fourstate: force or external write access.',
    11: 'Procedural deassign with --fourstate: force or external write access.',
    12: 'Tristate buffer with --fourstate: nondefault or externally driven target.',
    13: 'Tristate buffer with --fourstate: nondefault or externally driven target.',
    14: 'Blocking intra-assignment delay with --fourstate: partial or hierarchical target.',
    15: 'Blocking intra-assignment delay with --fourstate: nonlocal or nonpacked variable.',
    16: 'Blocking intra-assignment delay with --fourstate: partial or hierarchical target.',
    17: 'Blocking intra-assignment delay with --fourstate: force or external write access.',
}

for number, reason in reasons.items():
    log = f'{test.obj_dir}/case_{number}.log'
    golden = test.golden_filename.removesuffix('.out') + f'_{number}.out'
    top = {12: 'drive_input', 13: 'drive_inout'}.get(number, 't')
    # Input-net driving reaches an earlier ASSIGNIN guard. Bypass it only here
    # to verify that four-state lowering independently rejects this context.
    input_flags = ['-Wno-ASSIGNIN'] if number == 12 else []
    test.compile(
        verilator_flags2=[
            '--fourstate',
            '--timing',
            '-Wno-FUTURE',
            '--top-module',
            top,
            f'-DDRIVE_CASE_{number}',
        ] + input_flags,
        fails=True,
    )
    shutil.copyfile(test.obj_dir + '/vlt_compile.log', log)
    test.file_grep_not(log, r'Internal Error|syntax error')
    test.file_grep(log, r'^%Error-UNSUPPORTED: .*Unsupported:')
    test.file_grep(log, re.escape(reason))
    test.file_grep(log, r'%Error: Exiting due to (\d+) error\(s\)', 1)
    if not os.path.exists(golden):
        test.copy_if_golden(log, golden)
    test.files_identical(log, golden, is_logfile=True)
test.passes()
