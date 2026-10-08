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

test.scenarios('simulator')
fourstate = test.name == 't_fourstate_implicit_delay'
flags = ['--binary', '--trace', '--stats', '--no-sched-zero-delay', '-Wno-fatal']
if fourstate:
    flags += ['--fourstate']
test.compile(verilator_flags2=flags)
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Implicit delay checks: (\d+)', 301)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
if test.vlt_all:
    test.file_grep(test.stats, r'Timing, implicit timed sensitivities\s+(\d+)', 21)
expected = {}
widths = {}


def pattern(width, seed):
    states = '01xz' if fourstate else '01'
    return ''.join(states[(bit + seed) % len(states)] for bit in reversed(range(width)))


for width in (1, 7, 17, 33, 65, 129):
    prefix = f'w{width}.'
    zero, one = '0' * width, '1' * width
    first, second = pattern(width, 1), pattern(width, 2)
    third = 'z' * width if fourstate else one
    function_first = ''.join(char if char in '01' else 'x' for char in first)
    function_third = 'x' * width if fourstate else zero
    for name, timeline in (
        ('source', ((10, first), (11, zero), (20, third), (21, zero), (28, one))),
        ('result', ((13, first), (23, third), (31, one))),
        ('explicit_result', ((13, first), (23, third), (31, one))),
        ('function_result', ((13, function_first), (23, function_third), (31, zero))),
        ('hidden', ((15, one),)),
        ('delay_source', ((35, first), (36, second))),
        ('delay_result', ((38, first), (41, second))),
    ):
        add(expected, widths, prefix + name, width, zero)
        for timestamp, value in timeline:
            append(expected, prefix + name, timestamp, value)
    for name, times in (
        ('completions', (13, 23, 31)),
        ('explicit_completions', (13, 23, 31)),
        ('function_completions', (13, 23, 31)),
        ('delay_completions', (38, 41, 45)),
    ):
        add(expected, widths, prefix + name, 32, '0' * 32)
        for count, timestamp in enumerate(times, start=1):
            append(expected, prefix + name, timestamp, f'{count:032b}')
    for name, times in (
        ('completed_at', (13, 23, 31)),
        ('explicit_at', (13, 23, 31)),
        ('function_at', (13, 23, 31)),
        ('delay_at', (38, 41, 45)),
    ):
        add(expected, widths, prefix + name, 64, '0' * 64)
        for timestamp in times:
            append(expected, prefix + name, timestamp, f'{timestamp:064b}')
    add(expected, widths, prefix + 'delay_ticks', 4, '0011')
    append(expected, prefix + 'delay_ticks', 40, '0001')
    append(expected, prefix + 'delay_ticks', 43, '0010')
    add(expected, widths, prefix + 'done', 1, '0')
    append(expected, prefix + 'done', 49, '1')

for name, bits, initial, timeline in (
    ('never_hit', 1, '0', ()),
    ('indexed_source', 7, '1000001',
     ((19, '1000101'), (20, '1000100'), (24, ('x' if fourstate else '0') + '000100'),
      *(((25, 'z000100'),) if fourstate else ()),
      (29, '0000100' if fourstate else '1000100'))),
    ('index', 3, '000', ((10, '110'), (11, '001'), (15, '010'))),
    ('indexed_result', 1, '0', ((13, '1'), (18, '0'), (22, '1'))),
    ('indexed_completions', 32, '0' * 32,
     tuple((timestamp, f'{count:032b}') for count, timestamp in enumerate((13, 18, 22, 27, 32), 1))),
    ('indexed_at', 64, '0' * 64,
     tuple((timestamp, f'{timestamp:064b}') for timestamp in (13, 18, 22, 27, 32))),
    ('indexed_done', 1, '0', ((33, '1'),)),
    ('nested_source', 1, '0', ((10, '1'), (17, '0'))),
    ('nested_event', 1, '0', ((1, '1'), (13, '0'), (15, '1'), (20, '0'))),
    ('nested_result', 1, '0', ((12, '1'), (19, '0'))),
    ('nested_completions', 32, '0' * 32, ((13, f'{1:032b}'), (20, f'{2:032b}'))),
    ('nested_at', 64, '0' * 64, ((13, f'{13:064b}'), (20, f'{20:064b}'))),
    ('nested_done', 1, '0', ((22, '1'),)),
    ('done', 6, '000000', ((49, '111111'),)),
):
    key = 't.' + name
    add(expected, widths, key, bits, initial)
    for timestamp, value in timeline:
        append(expected, key, timestamp, value)
check_trace(test, expected, widths)
test.passes()
