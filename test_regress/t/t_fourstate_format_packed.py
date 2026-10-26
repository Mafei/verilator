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

# Literal values are independent of the formatter and its output-lowering code.
profiles = (
    ('MODULE', 'module_buffers', (
        ('number_initial', 'x' * 8),
        ('number_initial_unknown', '1'),
        ('ascii_initial', 'x' * 32),
        ('ascii_initial_unknown', '1'),
        ('number_written', '00110111'),
        ('number_written_unknown', '0'),
        ('ascii_written', '01000001010000100100001101000100'),
        ('ascii_written_unknown', '0'),
    )),
    ('TASK', 'task_buffers', (
        ('number_initial', 'x' * 8),
        ('number_initial_unknown', '1'),
        ('ascii_initial', 'x' * 32),
        ('ascii_initial_unknown', '1'),
        ('number_written', '00110111'),
        ('number_written_unknown', '0'),
        ('ascii_written', '01000001010000100100001101000100'),
        ('ascii_written_unknown', '0'),
    )),
    ('SELF', 'module_self', (
        ('self_initial', 'x' * 8),
        ('self_initial_unknown', '1'),
        ('self_written', '01111000'),
        ('self_written_unknown', '0'),
    )),
    ('TASK_SELF', 'task_self', (
        ('self_initial', 'x' * 8),
        ('self_initial_unknown', '1'),
        ('self_written', '01111000'),
        ('self_written_unknown', '0'),
    )),
    ('WIDTHS', 'typedef_widths', (
        ('w95_initial', 'x' * 95),
        ('w95_initial_unknown', '1'),
        ('w95_written', '0' * 80 + '100000101000010'),
        ('w95_written_unknown', '0'),
        ('w129_initial', 'x' * 129),
        ('w129_initial_unknown', '1'),
        ('w129_written', '0' * 106 + '10110000101100101011010'),
        ('w129_written_unknown', '0'),
        ('w29_initial', 'x' * 29),
        ('w29_initial_unknown', '1'),
        ('w29_written', '00000000000000000000001000011'),
        ('w29_written_unknown', '0'),
    )),
    ('CONTROLS', 'bit_string', (
        ('bit_number_initial', '00000000'),
        ('bit_ascii_initial', '00000000000000000000000000000000'),
        ('bit_number_written', '00110111'),
        ('bit_number_unknown', '0'),
        ('bit_ascii_written', '01000001010000100100001101000100'),
        ('bit_ascii_unknown', '0'),
        ('string_sformat', 'ABCD'),
        ('string_swrite', '7'),
    )),
    ('STRUCT', 'packed_struct', (
        ('struct_initial', 'x' * 16),
        ('struct_initial_unknown', '1'),
        ('struct_written', '0100000101000010'),
        ('struct_written_unknown', '0'),
        ('struct_hi', '01000001'),
        ('struct_lo', '01000010'),
    )),
)

base_dir = test.obj_dir
base_v_flags = test.v_flags.copy()
for macro, name, checks in profiles:
    test.obj_dir = base_dir + '/' + name
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    flags = ['--binary', '--fourstate', '--debug-check', '-Wno-FUTURE', '--top-module', 't']
    flags += ['--Mdir', test.obj_dir, '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1']
    test.compile(
        make_top_shell=False,
        make_main=False,
        v_flags2=['+define+PACKED_FORMAT_' + macro],
        verilator_flags2=flags,
    )
    test.file_grep_not(test.obj_dir + '/vlt_compile.log',
                       r'%Warning-|%Error|fatal error:|warning:')
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep_not(log, r'%Error|ERROR:|%Fatal')
    expected = ['PACKED_FORMAT_PROFILE name=' + name]
    expected += [
        'PACKED_FORMAT_CHECK n=' + str(number) + ' label=' + label + ' got=' + value +
        ' expected=' + value for number, (label, value) in enumerate(checks, 1)
    ]
    expected += [
        'PACKED_FORMAT_COMPLETE checks=' + str(len(checks)) + ' failures=0',
        'PACKED_FORMAT_PASSED checks=' + str(len(checks)) + ' failures=0',
        '*-* All Finished *-*',
    ]
    owned = [
        line for line in test.file_contents(log).splitlines()
        if line.startswith('PACKED_FORMAT_') or line == '*-* All Finished *-*'
    ]
    if owned != expected:
        test.error('Missing, duplicate, reordered or incorrect packed format output for ' + name)
    test.file_grep_count(log, r'^PACKED_FORMAT_CHECK ', len(checks))
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)

test.obj_dir = base_dir
test.v_flags = base_v_flags
test.passes()
