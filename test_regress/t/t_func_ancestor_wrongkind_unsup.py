#!/usr/bin/env python3
# DESCRIPTION: Verilator: Ancestor context prototype regression (UNEXECUTED)
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('linter')
# Generate diagnostic gold only with the real harness after source review.
test.compile(verilator_flags2=['--lint-only', '--timing', '--top-module', 't'],
             fails=True, expect_filename=test.golden_filename)
test.passes()
