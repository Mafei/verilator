#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('simulator')
test.compile(verilator_flags2=['--binary', '--trace', '--fourstate', '-Wno-FUTURE'])
test.execute()
test.file_grep(test.run_log_filename, r'^Sensitivity expression checks: (\d+)$', 61)
expected = {
    't.direct_value': [(0, '0000000'), (2, '0010010'), (3, '00x0010'), (4, '00z0010'),
                       (5, '0100100'), (6, 'xxxxxxx'), (10, '0110011'), (11, '0110100'),
                       (14, '0110110')],
    't.conditional_value': [(0, '0000000'), (2, '0010010'), (3, '00x0010'), (4, '00z0010'),
                            (12, '0110100'), (14, '0110110'), (15, '0x101xx')],
    't.readptr': [(0, '00'), (5, '01'), (6, '11'), (8, 'x1'), (9, 'z1'), (10, '10')],
    't.gate': [(0, '0'), (12, '1'), (15, 'x'), (16, 'z')],
}
check_trace(test, expected, {name: len(values[0][1]) for name, values in expected.items()})
test.passes()
