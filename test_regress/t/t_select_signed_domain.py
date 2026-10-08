#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import add, append, check_trace


def add_total_history(expected, widths):
    """Check the sum after all counters settle at each physical timestamp."""
    keys = [f'w{width}.checks' for width in (7, 17, 33, 65, 129)]
    keys += ['t.checks', 'min_bound.checks']
    times = sorted({time for key in keys for time, _value in expected[key]})
    totals = []
    for timestamp in times:
        total = 0
        for key in keys:
            prior = [value for time, value in expected[key] if time <= timestamp]
            total += int(prior[-1], 2)
        totals.append((timestamp, total))
    add(expected, widths, 't.total_checks', 32, f'{totals[0][1]:032b}')
    for timestamp, total in totals[1:]:
        append(expected, 't.total_checks', timestamp, f'{total:032b}')


def histories(reference_common=False):
    """Literal physical-time oracle, without using the compiler's index transforms."""
    expected = {}
    widths = {}

    def bits(value, width):
        return f'{value & ((1 << width) - 1):0{width}b}'

    def signal(key, width, initial, timeline=()):
        add(expected, widths, key, width, bits(initial, width))
        for timestamp, value in timeline:
            append(expected, key, timestamp, bits(value, width))

    for width in (7, 17, 33, 65, 129):
        prefix = f'w{width}.'
        one = (1 << width) - 1
        signal(prefix + 'down', width, one,
               ((9, one >> 1), (10, one), (11, one >> 1), (13, one)))
        for name in ('up', 'nonzero', 'negative'):
            signal(prefix + name, width, one)
        signal(prefix + 'memory_probe', 8, 0x55, ((9, 0), (10, 0x55)))
        indices = [(1, -1), (2, -2), (3, width), (4, width + 1), (5, 256), (6, -256)]
        if not reference_common:
            indices += [(7, 1 << 40), (8, -(1 << 40))]
        signal(prefix + 'index95', 95, 0, (*indices, (9, width - 1)))
        signal(prefix + 'index65', 65, 0, ((9, width - 1),))
        signal(prefix + 'valid_read65', 1, 0, ((9, 1),))
        signal(prefix + 'valid_read95', 1, 0)
        signal(prefix + 'sampled', 1, 0)
        signal(prefix + 'sampled_array', 8, 0)
        signal(prefix + 'calls', 32, 0, tuple((time, time - 10) for time in range(11, 16)))
        count = width + 4
        timeline = []
        for timestamp, _index in indices:
            count += width + 9
            timeline.append((timestamp, count))
        for timestamp, increment in ((9, 3), (10, width + 4), (11, 1), (12, 2),
                                     (13, 1), (14, 1), (15, width + 6)):
            count += increment
            timeline.append((timestamp, count))
        signal(prefix + 'checks', 32, width + 4, timeline)
        signal(prefix + 'done', 1, 0, ((16, 1),))

    signal('t.narrow_packed', 7, 0x7f, ((3, 0x77),))
    signal('t.narrow_array_probe', 8, 0x55, ((3, 0),))
    signal('t.narrow_index', 3, 0, ((1, -1), (2, -2), (3, 3)))
    signal('t.narrow_read', 1, 0)
    signal('t.narrow_array_read', 8, 0)
    signal('t.checks', 32, 0, ((1, 10), (2, 20), (3, 22), (20, 25)))
    signal('t.narrow_done', 1, 0, ((3, 1),))
    signal('t.done', 5, 0, ((16, 0x1f),))
    signal('t.min_done', 1, 0, ((4, 1),))
    signal('min_bound.down', 2, 2)
    signal('min_bound.up', 2, 2)
    signal('min_bound.index', 95, 0,
           ((1, -(1 << 31)), (2, -(1 << 31) + 1), (3, -(1 << 31) - 1), (4, -(1 << 31) + 2)))
    signal('min_bound.sampled', 1, 0, ((1, 1), (2, 0)))
    signal('min_bound.checks', 32, 0, ((1, 2), (2, 4), (3, 6), (4, 9)))
    signal('min_bound.done', 1, 0, ((4, 1),))
    add_total_history(expected, widths)
    return expected, widths


test.scenarios('vlt')
# Ascending ranges and 65/95-bit signed indices are deliberate test inputs.
# Keep all width/range diagnostics visible, and run the full domain by default.
test.compile(verilator_flags2=['--binary', '--trace', '--no-sched-zero-delay',
                              '--x-assign', '0', '-Wno-fatal'])
test.execute(logfile=test.run_log_filename)
test.file_grep(test.run_log_filename, r'Signed domain checks: (\d+)', 3265)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|FATAL:')
check_trace(test, *histories())
test.passes()
