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
profiles = [('reference', [])] if test.iv else [('two', []),
                                                ('four', ['--fourstate', '-Wno-FUTURE'])]
for profile, profile_flags in profiles:
    for case in range(8):
        timed = case in (0, 2, 4, 6)
        control = case in (5, 7)
        time = 1 if timed else 0
        test.obj_dir = base_dir + '/' + profile + '/case' + str(case)
        test.mkdir_ok(test.obj_dir)
        test.iv_flags = base_iv_flags + ['-o' + test.obj_dir + '/simiv']
        test.verilator_flags = [
            flag for flag in base_verilator_flags
            if flag not in ('--fourstate', '--no-fourstate', '-Wno-FUTURE')
        ]
        definitions = ['+define+FINISH_CALL_CASE=' + str(case)]
        if timed:
            definitions += ['+define+FINISH_CALL_TIMED']
        flags = ['--binary', '--top-module', 't', '--Mdir', test.obj_dir, '-j', '1']
        flags += ['-MAKEFLAGS', 'VM_PARALLEL_BUILDS=0']
        flags += ['--output-split-cfuncs', '1', '--timing' if timed else '--no-timing']
        test.compile(
            make_top_shell=False,
            make_main=False,
            v_flags2=definitions,
            verilator_flags2=flags + profile_flags,
        )
        log = test.obj_dir + '/run.log'
        run_flags = ['+DISABLE_TASK_FINISH'] if control else []
        # Icarus plusargs must follow simiv, as in t_finish_final_local.py.
        if test.iv:
            test.run(cmd=['vvp', '-N', test.obj_dir + '/simiv'] + run_flags,
                     logfile=log,
                     check_finished=True)
        else:
            test.execute(executable=test.obj_dir + '/' + test.vm_prefix,
                         logfile=log,
                         check_finished=True,
                         all_run_flags=run_flags)
        test.file_grep_not(log, r'UNREACHABLE|%Error|ERROR:|FATAL:')
        test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
        expected = ['CALLSTART case=' + str(case) + ' time=0']
        if case == 2:
            expected += ['CALLOUTER case=2 kind=plain time=0']
        elif case in (6, 7):
            expected += [
                'CALLOUTER case=' + str(case) + ' kind=params time=0 enable=' +
                str(int(not control)) + ' output=41 inout=43'
            ]
        if case in (0, 1, 2):
            expected += ['CALLENTER case=' + str(case) + ' kind=plain time=' + str(time)]
        else:
            expected += [
                'CALLENTER case=' + str(case) + ' kind=params time=' + str(time) + ' enable=' +
                str(int(not control)) + ' output=72 inout=84'
            ]
        if control:
            expected += ['CALLRETURN case=' + str(case) + ' kind=params time=0 output=72 inout=84']
            if case == 7:
                expected += ['CALLOUTERRETURN case=7 time=0 output=72 inout=84']
            expected += ['CALLCALLER case=' + str(case) + ' time=0 output=72 inout=84 done=1']
        expected += [
            'CALLFINAL case=' + str(case) + ' time=' + str(time) + ' output=' +
            ('72' if control else '19') + ' inout=' + ('84' if control else '23') + ' done=' +
            str(int(control)) + ' q=0'
        ]
        owned = [line for line in test.file_contents(log).splitlines() if line.startswith('CALL')]
        if owned != expected:
            test.error('Termination/copyback output mismatch: got=' + repr(owned) + ' expected=' +
                       repr(expected))

test.obj_dir = base_dir
test.iv_flags = base_iv_flags
test.verilator_flags = base_verilator_flags
test.passes()
