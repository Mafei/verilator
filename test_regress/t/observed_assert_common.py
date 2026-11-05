#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2024 Wilson Snyder
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Check observed assertion integration without relying on action ordering."""


def finish(test, fourstate=False):
    """Reject statements after finish within an action, with both task forms."""
    test.top_filename = 't/t_assert_obs_finish.v'
    base_dir = test.obj_dir
    for noinline in (False, True):
        test.obj_dir = base_dir + ('/noinline' if noinline else '/inline')
        test.mkdir_ok(test.obj_dir)
        flags = [
            '--binary', '--assert', '--timing', '--top-module', 't', '--Mdir', test.obj_dir, '-j',
            '1'
        ]
        if fourstate:
            flags += ['--fourstate', '-Wno-FUTURE']
        definitions = ['+define+OBS_FINISH_NOINLINE'] if noinline else []
        test.compile(make_top_shell=False,
                     make_main=False,
                     v_flags2=definitions,
                     verilator_flags2=flags)
        log = test.obj_dir + '/run.log'
        test.execute(executable=test.obj_dir + '/' + test.vm_prefix,
                     logfile=log,
                     check_finished=True)
        test.file_grep_count(log, r'^OBS_FINISH_ENTER$', 1)
        test.file_grep_count(log, r'^OBS_FINISH_FINAL$', 1)
        test.file_grep_count(log, r'Verilog \$finish', 1)
        test.file_grep_not(log, r'OBS_FINISH_LATE_IN_ACTION|%Error|ERROR:')
        # Another queued action may run first. With this single-threaded model,
        # its output must precede the actual finish diagnostic if it occurs.
        lines = test.file_contents(log).splitlines()
        stops = [index for index, line in enumerate(lines) if 'Verilog $finish' in line]
        if len(stops) == 1 and any(index > stops[0] and line == 'OBS_FINISH_OTHER_ACTION'
                                   for index, line in enumerate(lines)):
            test.error('Observed action continued after the finish request')
    test.obj_dir = base_dir
