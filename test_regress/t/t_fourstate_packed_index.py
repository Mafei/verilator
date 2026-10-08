#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

# Wide packed indexes exercise normative bounds that Icarus truncates to 32 bits.
test.scenarios('vlt_all')

# Deliberately exercise ascending declarations and narrower/wider selection indexes.
test.compile(verilator_flags2=[
    '--binary', '--fourstate', '--debug-check', '-Wno-FUTURE',
    '-Wno-ASCRANGE', '-Wno-WIDTHEXPAND', '-Wno-WIDTHTRUNC',
])
test.execute()
test.passes()
