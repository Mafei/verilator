#!/usr/bin/env python3
# DESCRIPTION: Verilator: Trace writes after a split coroutine resumes
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import hashlib
import json
import os
import re
import shlex

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
test.timeout(120)
base_dir = test.obj_dir
base_flags = [flag for flag in test.v_flags if 'TEST_DUMPFILE' not in flag]
expected = {'t.done': [(0, '00'), (1, '11')]}
for child in ('u0', 'u1'):
    expected[f't.{child}.done'] = [(0, '0'), (1, '1')]
    for name, value in (('phase', 1), ('value_a', 7), ('value_b', 19)):
        expected[f't.{child}.{name}'] = [(0, '0' * 32), (1, format(value, '032b'))]
widths = {name: len(history[0][1]) for name, history in expected.items()}
profiles = []
for profile in ('two_state', 'four_state'):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_flags.copy()
    flags = [
        '--binary', '--trace', '--top-module', 't', '--debug-check', '--output-split-cfuncs', '1',
        '--Mdir', test.obj_dir, '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1', '-CFLAGS',
        '-Werror'
    ]
    if os.environ.get('CXX'):
        flags += ['-MAKEFLAGS', shlex.quote('CXX=' + os.environ['CXX'])]
        flags += ['-MAKEFLAGS', shlex.quote('LINK=' + os.environ['CXX'])]
    if profile == 'four_state':
        flags += ['--fourstate', '-Wno-FUTURE']
    test.compile(make_top_shell=False, make_main=False, verilator_flags2=flags)
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep_count(log, r'^TRACE_MODEL_PASS done=11$', 1)
    test.file_grep_count(log, r'^Trace resume checkpoints: 9$', 1)
    check_trace(test, expected, widths)
    with open(test.trace_filename, 'rb') as stream:
        trace = stream.read()
    declarations = []
    scopes = []
    for line in trace.decode('ascii').splitlines():
        fields = line.split()
        if fields and fields[0] == '$scope':
            scopes.append(fields[2])
        elif fields and fields[0] == '$upscope':
            scopes.pop()
        elif fields and fields[0] == '$var':
            name = '.'.join(scopes + [fields[4]])
            if name in widths:
                declarations.append({
                    'name': name,
                    'kind': fields[1],
                    'width': int(fields[2]),
                    'code': fields[3]
                })
    if ({row['name']: row['width'] for row in declarations} != widths or len(declarations) != 9):
        test.error('Trace resume hierarchy or declaration width differs')
    if not re.search(rb'\$timescale\s+1ps\s+\$end', trace):
        test.error('Trace resume precision differs')
    if test.errors or test.errors_keep_going:
        continue
    proof = {
        'profile': profile,
        'complete_histories': expected,
        'sv_checkpoints': 9,
        'hierarchical_declarations': declarations,
        'source_port_connections': {
            't.u0.done': 't.done[0]',
            't.u1.done': 't.done[1]'
        },
        'wave': test.trace_filename,
        'wave_bytes': len(trace),
        'wave_sha256': hashlib.sha256(trace).hexdigest()
    }
    with open(test.obj_dir + '/trace_resume_metadata.json', 'w', encoding='ascii') as stream:
        json.dump(proof, stream, indent=2, sort_keys=True)
        stream.write('\n')
    profiles.append(proof)
    print(f'Trace resume profile: {profile} histories=9 checkpoints=9 '
          f'sha256={proof["wave_sha256"]}')
test.obj_dir = base_dir
if len(profiles) != 2:
    test.error('Trace resume did not complete both profiles')
with open(base_dir + '/trace_resume_profiles.json', 'w', encoding='ascii') as stream:
    json.dump(profiles, stream, indent=2, sort_keys=True)
    stream.write('\n')
test.passes()
