#!/usr/bin/env python3
# DESCRIPTION: Verilator: Named non-ANSI port diagnostic contract
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

# The bounded invalid-definition contract follows the cited 2005/SV-BC 2012 rule.
# Fixed Icarus acceptance is preserved separately, not used as a negative pass.
test.scenarios('linter')
# Only this new test's actual golden may be generated; old golds stay unchanged.
test.lint(verilator_flags2=['--fourstate', '-Wno-FUTURE', '--top-module', 't'],
          fails=True,
          expect_filename=test.golden_filename)
log = test.obj_dir + '/vlt_compile.log'
test.file_grep_not(log, r'Internal Error|Segmentation fault|Aborting|Assertion')
test.file_grep_count(log, "^%Error: .*Duplicate declaration of port: 'same'$", 1)
test.file_grep_not(log, r'^%Error-UNSUPPORTED:')
test.passes()
