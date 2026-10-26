#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('simulator')
test.compile(verilator_flags2=['--binary', '--fourstate', '--build-jobs', '1', '-Wno-FUTURE'],
             make_flags=['-j1'])
test.execute()
test.file_grep(test.run_log_filename, r'^Scalar reduction checks: (\d+)$', 1094)
test.passes()
