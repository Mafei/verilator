#!/usr/bin/env python3
# DESCRIPTION: Verilator: Named non-ANSI port diagnostic contract
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('linter')
# Only this new test's actual golden may be generated; old golds stay unchanged.
test.lint(verilator_flags2=['--fourstate', '-Wno-FUTURE', '--top-module', 't'],
          fails=True,
          expect_filename=test.golden_filename)
log = test.obj_dir + '/vlt_compile.log'
test.file_grep_not(log, r'Internal Error|Segmentation fault|Aborting|Assertion')
test.file_grep_count(
    log,
    '^%Error-UNSUPPORTED: .*Unsupported: Named non-ANSI ports require direct OUTPUT wires\\.$', 1)
test.file_grep_count(log, r'^%Error-UNSUPPORTED:', 1)
test.passes()
