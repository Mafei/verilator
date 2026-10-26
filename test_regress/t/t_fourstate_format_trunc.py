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

base_dir = test.obj_dir
base_v_flags = test.v_flags.copy()
runtime_cases = (
    'byte_empty',
    'byte_exact',
    'byte_long',
    'bit7_high',
    'half_empty',
    'half_short',
    'half_exact',
    'half_long',
    'bit9_exact',
    'bit15_high',
    'word_empty',
    'word_short',
    'word_exact',
    'word_long',
    'bit17_long',
    'bit29_exact',
    'quad_empty',
    'quad_short',
    'quad_exact',
    'quad_long',
    'bit33_long',
    'bit63_high',
    'wide65_empty',
    'wide65_short',
    'wide65_exact',
    'wide65_long',
    'wide95_empty',
    'wide95_short',
    'wide95_exact',
    'wide95_long',
    'wide95_high',
    'wide129_empty',
    'wide129_short',
    'wide129_exact',
    'wide129_long',
    'wide129_high',
)
sv_values = (
    ('byte_long', 8, 0x42),
    ('byte_exact', 8, 0x41),
    ('half_partial', 15, 0x7f42),
    ('word_partial', 29, 0x01424344),
    ('word_empty', 29, 0),
    ('wide65_long', 65, 0x14243444546474849),
    ('wide129_long', 129, 0x142434445464748494a4b4c4d4e4f5051),
    ('wide129_short', 129, 0x4142),
    ('dynamic_long', 32, 0x41424344),
)
for profile in ('runtime', 'two_state', 'four_state'):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    flags = ['--debug-check', '--top-module', 't', '--Mdir', test.obj_dir]
    flags += ['-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1']
    if profile == 'runtime':
        flags += ['--cc', '--no-timing', '-CFLAGS', '-std=c++14']
        test.compile(
            make_top_shell=False,
            make_main=False,
            v_flags2=['+define+FORMAT_TRUNC_RUNTIME', '--exe', test.pli_filename],
            verilator_flags2=flags,
        )
    else:
        flags += ['--binary']
        if profile == 'four_state':
            flags += ['--fourstate', '-Wno-FUTURE']
        defines = ['+define+FORMAT_TRUNC_FOUR_STATE'] if profile == 'four_state' else []
        test.compile(
            make_top_shell=False,
            make_main=False,
            v_flags2=defines,
            verilator_flags2=flags,
        )
    test.file_grep_not(test.obj_dir + '/vlt_compile.log',
                       r'%Warning-|%Error|fatal error:|warning:')
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep_not(log, r'%Error|ERROR:|%Fatal')
    expected = []
    if profile == 'runtime':
        items = [(name, api, kind) for name in runtime_cases for api in ('char', 'string')
                 for kind in ('value', 'canary')]
        items += [('unpacked_string', api, 'value') for api in ('char', 'string')]
        for number, (name, api, kind) in enumerate(items, 1):
            expected.append('PACKED_TRUNC_RUNTIME_CHECK n=' + str(number) + ' case=' + name +
                            ' api=' + api + ' kind=' + kind + ' got=1 expected=1')
        expected.append('PACKED_TRUNC_RUNTIME_PASS checks=146')
    else:
        items = []
        for label, width, value in sv_values:
            items += [(label, format(value, '0' + str(width) + 'b')), (label + '_unknown', '0')]
        for number, (label, value) in enumerate(items, 1):
            expected.append('PACKED_TRUNC_CHECK n=' + str(number) + ' label=' + label + ' got=' +
                            value + ' expected=' + value)
        expected += [
            'PACKED_TRUNC_COMPLETE checks=18 failures=0', 'PACKED_TRUNC_PASS checks=18 failures=0'
        ]
    expected.append('*-* All Finished *-*')
    owned = [
        line for line in test.file_contents(log).splitlines()
        if line.startswith('PACKED_TRUNC_') or line == '*-* All Finished *-*'
    ]
    if owned != expected:
        test.error('Missing, duplicate, reordered or incorrect packed truncation output: ' +
                   profile)
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)

test.obj_dir = base_dir
test.v_flags = base_v_flags
test.passes()
