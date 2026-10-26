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
for flags in (['--language', '1364-2001'], ['--default-language', '1364-2001'],
              ['--language', '1364-2001-noconfig',
               '+1364-2001ext+v'], ['--default-language', '1364-2001-noconfig',
                                    '+1364-2001ext+v']):
    test.lint(verilator_flags2=flags, fails=True, expect_filename=test.golden_filename)
    test.file_grep_not(test.obj_dir + '/vlt_compile.log', r'Unknown language|Internal Error')
test.passes()
