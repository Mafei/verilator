#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import shlex

import vltest_bootstrap

test.scenarios('vlt')

base_dir = test.obj_dir
base_v_flags = test.v_flags.copy()
values = (
    ('zero', '0'),
    ('negative_zero', '0'),
    ('positive', '1'),
    ('negative', '-1'),
    ('positive_half', '2'),
    ('negative_half', '-2'),
    ('positive_half_three', '3'),
    ('negative_half_three', '-3'),
    ('positive_round', '124'),
    ('negative_round', '-124'),
    ('int32_max', '2147483647'),
    ('int32_min', '-2147483648'),
)
mixed = '1|1.4e+00|1.4|1|1.4|1.4ns|-2|a5'
for state in ('two_state', 'four_state'):
    for wide in (0, 1):
        profile = state + ('_wide' if wide else '_minimum')
        test.obj_dir = base_dir + '/' + profile
        test.mkdir_ok(test.obj_dir)
        test.v_flags = base_v_flags.copy()
        flags = [
            '--binary', '--no-timing', '--debug-check', '--top-module', 't', '--Mdir',
            test.obj_dir, '-CFLAGS', '-std=c++14', '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1'
        ]
        if state == 'four_state':
            flags += ['--fourstate', '-Wno-FUTURE']
        test.compile(make_top_shell=False, make_main=False, verilator_flags2=flags)
        test.file_grep_not(test.obj_dir + '/vlt_compile.log',
                           r'%Warning-|%Error|fatal error:|warning:')
        log = test.obj_dir + '/run.log'
        test.execute(executable=test.obj_dir + '/' + test.vm_prefix,
                     logfile=log,
                     check_finished=True,
                     all_run_flags=[
                         '+FMT=%8d' if wide else '+FMT=%0d',
                         shlex.quote('+MIX=%0d|%.1e|%.1f|%.1g|%p|%t|%0d|%0h'), '+WIDE=' + str(wide)
                     ])
        expected = []
        number = 0
        for label, value in values + (('mixed', mixed), ):
            value = value.rjust(8) if wide and label != 'mixed' else value
            for api in ('sformatf', 'sformat', 'packed_sformat'):
                number += 1
                actual_value = (format(
                    int.from_bytes(value.encode('ascii'), 'big') &
                    ((1 << 95) - 1), '024x') if api == 'packed_sformat' else value)
                expected.append('DYNAMIC_REAL_CHECK n=' + str(number) + ' case=' + label +
                                ' api=' + api + ' got=' + actual_value + ' expected=' +
                                actual_value)
        expected += [
            'DYNAMIC_REAL_COMPLETE checks=39 failures=0', 'DYNAMIC_REAL_PASS checks=39 failures=0',
            '*-* All Finished *-*'
        ]
        observed = [
            line for line in test.file_contents(log).splitlines()
            if line.startswith('DYNAMIC_REAL_') or line == '*-* All Finished *-*'
        ]
        if observed != expected:
            test.error('Missing, duplicate, reordered or incorrect real output: ' + profile)
        test.file_grep_not(log, r'%Error|ERROR:|%Fatal')
        test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)

test.obj_dir = base_dir
test.v_flags = base_v_flags
test.passes()
