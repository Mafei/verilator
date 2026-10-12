#!/usr/bin/env python3
# DESCRIPTION: Verilator: Independent event-controlled NBA controls
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

from pathlib import Path

import vltest_bootstrap
from event_nba_oracle import check

test.scenarios('vlt')
test.compile(verilator_flags2=[
    '--binary',
    '--trace',
    '--fourstate',
    '--debug-check',
    '-Wno-FUTURE',
    '-Wno-ASCRANGE',
    '--output-split',
    '1000',
    '--output-split-cfuncs',
    '50',
])
test.execute()
try:
    result = check('race', Path(test.trace_filename),
                   Path(test.run_log_filename))
except ValueError as error:
    test.error(str(error))
else:
    print(f'Event NBA waveform checks: {result["signals"]}')
test.passes()
