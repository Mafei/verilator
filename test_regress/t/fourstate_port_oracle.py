#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

"""Character-vector port oracles independent of generated value/XZ halves."""

from fourstate_resolve_oracle import add, append

WIDTHS = (7, 33, 65, 95)


def _values(width):
    return [
        ''.join('01xz'[index % 4] for index in reversed(range(width))),
        ''.join('1' if index % 3 == 1 else '0' for index in reversed(range(width))),
        'z' * width,
        'x' * width,
        ''.join('0' if index % 3 == 1 else '1' for index in reversed(range(width))),
    ]


def port_init():
    expected = {}
    widths = {}
    add(expected, widths, 't.total_checks', 32, '0' * 32)
    for width in WIDTHS:
        scope = f't.w{width}.'
        add(expected, widths, scope + 'data', width, '0' * width)
        ports = {
            **{f'{kind}_{target}': default
               for kind, default in (('default', 'x'), ('explicit', 'x'),
                                     ('implicit', 'z'), ('net', 'z'))
               for target in ('logic', 'var', 'wire')},
            'ascending_default': 'x',
            'ascending_net': 'z',
        }
        for name, default in ports.items():
            add(expected, widths, scope + name, 2 * width, default * width + '0' * width)
        for name, default in (('output_unconnected_default', 'x'),
                              ('output_unconnected_net', 'z')):
            add(expected, widths, scope + name, 2 * width, default * (2 * width))
        add(expected, widths, scope + 'checks', 32, '0' * 32)
        add(expected, widths, scope + 'done', 1, '0')
        for phase, value in enumerate(_values(width)):
            timestamp = (phase + 1) * 1000
            append(expected, scope + 'data', timestamp, value)
            for name, default in ports.items():
                append(expected, scope + name, timestamp, default * width + value)
            append(expected, scope + 'checks', timestamp + 1000, format(16 * (phase + 1), '032b'))
        append(expected, scope + 'done', 6000, '1')
    for phase in range(5):
        append(expected, 't.total_checks', (phase + 2) * 1000, format(64 * (phase + 1), '032b'))
    return expected, widths


def port_partial():
    expected = {}
    widths = {}
    add(expected, widths, 't.total_checks', 32, '0' * 32)
    for width in WIDTHS:
        scope = f't.w{width}.'
        cut = width // 2
        add(expected, widths, scope + 'data', width, '0' * width)
        ports = {'output_default': 'x', 'output_explicit_var': 'x', 'output_net': 'z',
                 'variable_to_net': 'x', 'net_to_variable': 'z'}
        for name, default in ports.items():
            add(expected, widths, scope + name, 2 * width, default * width + '0' * width)
        packed = {'concat_variable': 'x', 'concat_explicit_var': 'x', 'concat_net': 'z'}
        for name, default in packed.items():
            low = default * (width - 1) + '0' + default * width + '0' * (width - 1) + default
            add(expected, widths, scope + name, 6 * width, default * (3 * width) + low)
        for name, default in (('cross_variable', 'x'), ('cross_net', 'z')):
            value = default * (width - cut) + '0' * cut + default * cut + '0' * (width - cut)
            add(expected, widths, scope + name, 2 * width, value)
        add(expected, widths, scope + 'checks', 32, '0' * 32)
        add(expected, widths, scope + 'done', 1, '0')
        for phase, value in enumerate(_values(width)):
            timestamp = (phase + 1) * 1000
            append(expected, scope + 'data', timestamp, value)
            for name, default in ports.items():
                append(expected, scope + name, timestamp, default * width + value)
            for name, default in packed.items():
                low = (default * (width - 1) + value[0] + default * width
                       + value[1:] + default)
                append(expected, scope + name, timestamp, default * (3 * width) + low)
            for name, default in (('cross_variable', 'x'), ('cross_net', 'z')):
                vector = default * (width - cut) + value[:cut] + default * cut + value[cut:]
                append(expected, scope + name, timestamp, vector)
            append(expected, scope + 'checks', timestamp + 1000, format(19 * (phase + 1), '032b'))
        append(expected, scope + 'done', 6000, '1')
    for phase in range(5):
        append(expected, 't.total_checks', (phase + 2) * 1000, format(76 * (phase + 1), '032b'))
    return expected, widths
