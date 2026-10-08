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

# Exercise word-sized indexes and both declaration directions with dynamic X/Z data.
test.compile(verilator_flags2=[
    '--binary', '--fourstate', '--debug-check', '-Wno-FUTURE', '-Wno-fatal',
])
test.execute()
test.passes()
