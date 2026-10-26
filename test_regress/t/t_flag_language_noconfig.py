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
for option in ('--language', '--default-language'):
    test.lint(verilator_flags2=[option, '1364-2001-noconfig'])
test.lint(verilator_flags2=['--language', '1800-2023', '--language', '1364-2001-NOCONFIG'])
test.passes()
