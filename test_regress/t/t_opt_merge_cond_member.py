#!/usr/bin/env python3
# DESCRIPTION: Verilator: Conditional code motion across aliased class members
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
test.compile(verilator_flags2=['--binary', '--build-jobs', '1'], make_flags=['-j1'])
test.execute()
test.file_grep(test.run_log_filename, r'^Aliased member checks: (\d+)$', 6)
test.passes()
