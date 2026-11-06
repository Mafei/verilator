#!/usr/bin/env python3
# DESCRIPTION: Verilator: Delayed class NBA bounds controls
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Check delayed writes against independently declared VCD transitions."""

import re
from pathlib import Path


def check(path):
    """Require the two 8-bit targets to change only at the 2ns NBA commit."""
    expected = {
        'bank0': [(0, '00000000'), (2000, '10xz01z1')],
        'bank1': [(0, '00000000'), (2000, 'z10x1100')],
    }
    trace = Path(path).read_text(encoding='ascii')
    if not re.search(r'\$timescale\s+1ps\s+\$end', trace):
        raise ValueError('Class bounds VCD precision differs from 1ps')
    scopes = []
    codes = {}
    actual = {name: [] for name in expected}
    timestamp = 0
    for line in trace.splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == '$scope':
            scopes.append(words[2])
        elif words[0] == '$upscope':
            scopes.pop()
        elif words[0] == '$var' and scopes and scopes[-1] == 't':
            if words[4] in expected:
                if int(words[2]) != 8:
                    raise ValueError('Class bounds VCD target width differs from 8')
                codes.setdefault(words[3], []).append(words[4])
        elif words[0].startswith('#'):
            timestamp = int(words[0][1:])
        elif words[0].startswith('b'):
            value = words[0][1:].lower()
            for name in codes.get(words[1], []):
                value = value.rjust(8, value[0] if value[0] in 'xz' else '0')
                history = actual[name]
                if not history or history[-1][1] != value:
                    history.append((timestamp, value))
    if actual != expected:
        raise ValueError(f'Class bounds VCD transitions differ: {actual}, expected {expected}')
    return {'signals': 2, 'transitions': 4}
