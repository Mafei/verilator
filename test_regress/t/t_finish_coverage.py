#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import os

import vltest_bootstrap

test.scenarios('vlt')

source = test.file_contents(test.top_filename).splitlines()
markers = ('DIRECT_COVER_LINE', 'INLINE_COVER_LINE', 'NOINLINE_COVER_LINE', 'INLINE_CALL_LINE',
           'NOINLINE_CALL_LINE')
lines = {
    marker: next(index for index, line in enumerate(source, 1) if marker in line)
    for marker in markers
}
base_dir = test.obj_dir
for fourstate in (False, True):
    test.obj_dir = base_dir + ('/fourstate' if fourstate else '/twostate')
    test.mkdir_ok(test.obj_dir)
    flags = ['--binary', '--timing', '--coverage', '--assert', '--Mdir', test.obj_dir]
    if fourstate:
        flags += ['--fourstate', '-Wno-FUTURE']
    test.compile(make_top_shell=False, make_main=False, verilator_flags2=flags)
    for mode in range(3):
        prefix = test.obj_dir + '/case' + str(mode)
        coverage = prefix + '.dat'
        info = prefix + '.info'
        log = prefix + '.log'
        test.execute(executable=test.obj_dir + '/' + test.vm_prefix,
                     logfile=log,
                     all_run_flags=['+MODE=' + str(mode), '+verilator+coverage+file+' + coverage])
        test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
        test.file_grep_not(log, r'UNREACHABLE|%Error|ERROR:')
        test.run(cmd=[
            os.environ['VERILATOR_ROOT'] + '/bin/verilator_coverage', '--filter-type', 'line',
            '--write-info', info, coverage
        ],
                 verilator_run=True)
        active = ({'DIRECT_COVER_LINE'}, {'INLINE_COVER_LINE', 'INLINE_CALL_LINE'},
                  {'NOINLINE_COVER_LINE', 'NOINLINE_CALL_LINE'})[mode]
        for marker, line in lines.items():
            test.file_grep_count(
                info, r'^DA:' + str(line) + ',' + ('1' if marker in active else '0') + '$', 1)
        test.file_grep_count(coverage, r'^C .*v_user/.* 0$', 1)

test.obj_dir = base_dir
test.passes()
