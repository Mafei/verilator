#!/usr/bin/env python3
# DESCRIPTION: Verilator: MT exec-graph complete-wave controls
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import json
from pathlib import Path

import vltest_bootstrap
from mt_trace_oracle import verify

test.scenarios('vltmt')
test.pli_filename = 't/t_fourstate_mt_trace.cpp'
base_dir = test.obj_dir
base_flags = [flag for flag in test.v_flags if 'TEST_DUMPFILE' not in flag]
records = []
for profile, fourstate in (('two_state', False), ('four_state', True)):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_flags.copy()
    options = ['--fourstate', '-Wno-FUTURE'] if fourstate else []
    test.compile(make_main=False,
                 make_top_shell=False,
                 threads=2,
                 v_flags2=['+define+FOURSTATE'] if fourstate else [],
                 verilator_flags2=[
                     '--cc', '--exe', test.pli_filename, '--Mdir', test.obj_dir, '--trace',
                     '--no-timing', '--top-module', 't', '--threads-max-mtasks', '1',
                     '-Wno-UNOPTTHREADS', '--x-assign', '0', '--x-initial', '0', *options
                 ])
    log_path = test.obj_dir + '/run.log'
    test.execute(logfile=log_path, check_finished=True)
    record = verify(log_path, test.obj_dir + '/simx.vcd', fourstate)
    records.append(record)
    print('MT_TRACE_COMPLETE ' + json.dumps(record))
test.obj_dir = base_dir
Path(base_dir + '/whole-wave-results.json').write_text(json.dumps(records, indent=2) + '\n',
                                                       encoding='ascii')
test.passes()
