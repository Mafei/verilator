#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt', 'iv')

base_dir = test.obj_dir
base_iv_flags = [flag for flag in test.iv_flags if not flag.startswith('-o')]
base_verilator_flags = test.verilator_flags[:]
profiles = [('reference', [])] if test.iv else [
    ('two', []), ('four', ['--fourstate', '-Wno-FUTURE'])
]
for profile, profile_flags in profiles:
    for case in range(6):
        test.obj_dir = base_dir + '/' + profile + '/case' + str(case)
        test.mkdir_ok(test.obj_dir)
        test.iv_flags = base_iv_flags + ['-o' + test.obj_dir + '/simiv']
        test.verilator_flags = [flag for flag in base_verilator_flags
                                if flag not in ('--fourstate', '--no-fourstate', '-Wno-FUTURE')]
        flags = ['--binary', '--top-module', 't', '--Mdir', test.obj_dir, '-j', '1']
        flags += ['-MAKEFLAGS', 'VM_PARALLEL_BUILDS=0', '--output-split', '1']
        flags += ['--output-split-cfuncs', '1'] + profile_flags
        test.compile(
            make_top_shell=False,
            make_main=False,
            v_flags2=['+define+FINAL_MULTI_CASE=' + str(case)],
            verilator_flags2=flags,
        )
        log = test.obj_dir + '/run.log'
        test.execute(
            executable=test.obj_dir + '/' + test.vm_prefix,
            logfile=log,
            check_finished=True,
            iv_run_flags=['-N'],
        )
        test.file_grep_not(log, r'UNREACHABLE|%Error|ERROR:|FATAL:')
        test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
        owned = [line for line in test.file_contents(log).splitlines()
                 if line.startswith(('FINALSTART ', 'FINALMULTI '))]
        start = 'FINALSTART case=' + str(case) + ' time=1'
        if not owned or owned[0] != start:
            test.error('Missing or reordered source finish prefix: ' + repr(owned))
        finals = owned[1:]
        if case == 0:
            allowed = [['FINALMULTI case=0 tag=A time=1'],
                       ['FINALMULTI case=0 tag=B time=1']]
            if finals not in allowed:
                test.error('Expected exactly one A or B final prefix: ' + repr(finals))
        elif case in (3, 4):
            allowed = [['FINALMULTI case=' + str(case) + ' tag=' + str(tag) + ' time=1']
                       for tag in range(3)]
            if finals not in allowed:
                test.error('Expected exactly one runtime-instance final: ' + repr(finals))
        else:
            expected = ['FINALMULTI case=' + str(case) + ' tag=' + str(tag) + ' time=1'
                        for tag in range(3)]
            if sorted(finals) != expected:
                test.error('Expected all ordinary finals in any order: ' + repr(finals))

test.obj_dir = base_dir
test.iv_flags = base_iv_flags
test.verilator_flags = base_verilator_flags
test.passes()
