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
import re
import subprocess
from pathlib import Path

from fourstate_resolve_oracle import check_trace

WIDTHS = (1, 8, 9, 32, 33, 64, 65, 128, 129, 256, 257, 301)
TIMES = (0, 5, 11, 18, 26, 35)
STATES = ('1', 'x', '0', 'z', '1', 'x')


def histories():
    expected = {}
    for width in WIDTHS:
        for name in ('a', 'real_alias', 'opposite'):
            chars = STATES if name != 'opposite' else ('x', '1', 'z', '0', 'x', '1')
            expected[f't.w{width}.{name}'] = list(zip(TIMES, [c * width for c in chars]))
    for name, width in (('wide_slice.cross_word', 65), ('wide_slice.tail', 31),
                        ('small_slice.cross_word', 33), ('small_slice.tail', 31)):
        expected['t.' + name] = list(zip(TIMES, [c * width for c in STATES]))
    return expected


def declarations(contents):
    scopes = []
    result = {}
    for line in contents.splitlines():
        fields = line.split()
        if fields[:1] == ['$scope']:
            scopes.append(fields[2])
        elif fields[:1] == ['$upscope']:
            scopes.pop()
        elif fields[:1] == ['$var']:
            result['.'.join(scopes + [fields[4]])] = {
                'kind': fields[1],
                'width': int(fields[2]),
                'code': fields[3],
                'range': fields[5] if fields[5] != '$end' else None
            }
    return result


def saif_records(contents):
    # Parse S-expressions, keeping hierarchy: identical net names in different
    # instances must never overwrite one another in the oracle.
    stack = [[]]
    for token in re.findall(r'\(|\)|[^\s()]+', contents):
        if token == '(':
            child = []
            stack[-1].append(child)
            stack.append(child)
        elif token == ')':
            stack.pop()
        else:
            stack[-1].append(token)
    result = {}

    def walk(node, scopes):
        if not isinstance(node, list) or not node:
            return
        if node[0] == 'INSTANCE':
            scopes = scopes + [node[1]]
        if node[0] == 'NET':
            for item in node[1:]:
                name = '.'.join(scopes + [item[0].replace('\\', '')])
                result[name] = {field[0]: int(field[1]) for field in item[1:]}
        for item in node:
            if isinstance(item, list):
                walk(item, scopes)

    for node in stack[0]:
        walk(node, [])
    return result


def check_fst(test, path, expected, widths):
    # Header offset follows fstcpp_file.h: 9-byte block header, eight 64-bit fields.
    data = Path(path).read_bytes()
    if len(data) < 74 or data[0] != 0 or int.from_bytes(data[73:74], 'big', signed=True) != -12:
        test.error('FST header does not establish 1ps physical timestamps')
    result = subprocess.run(['wavecat', '--time-pound', path],
                            capture_output=True,
                            text=True,
                            check=False)
    Path(test.obj_dir + '/fst-decoded.log').write_text(result.stdout + result.stderr)
    if result.returncode or result.stderr.strip():
        test.error(f'FST decoding failed: exit={result.returncode}: {result.stderr[:500]}')
    samples = {name: {} for name in expected}
    for line in result.stdout.splitlines():
        match = re.fullmatch(r'#(\d+)\s+(.+?)\s+([01xzXZ]+)', line)
        if not match:
            continue
        name = re.sub(r' \[-?\d+:-?\d+\]$', '', match[2])
        if name not in samples:
            continue
        value = match[3].lower()
        value = value.rjust(widths[name], value[0] if value[0] in 'xz' else '0')
        samples[name][int(match[1])] = value
    actual = {}
    for name, rows in samples.items():
        compact = []
        for stamp, value in sorted(rows.items()):
            if not compact or compact[-1][1] != value:
                compact.append((stamp, value))
        actual[name] = compact
    if actual != expected:
        bad = [name for name in expected if actual[name] != expected[name]]
        Path(test.obj_dir + '/fst-mismatch.json').write_text(
            json.dumps({
                'actual': actual,
                'expected': expected
            }, indent=2) + '\n')
        test.error(f'FST complete value/time histories differ: {bad}')
    attrs = subprocess.run(['wavecat', '--attrs', path],
                           capture_output=True,
                           text=True,
                           check=False)
    if attrs.returncode:
        test.error('FST declaration metadata could not be read')
    return {
        'timescale_exponent':
        -12,
        'histories':
        actual,
        'declaration_metadata':
        attrs.stdout,
        'direct_FST_alias_ids':
        'Not exposed by wavecat; shared-address counterexample is checked by histories'
    }


def check_vcd(test, path, expected, widths):

    class View:
        trace_filename = path

        def error(self, message):
            test.error(message)

    check_trace(View(), expected, widths)


def run(test, profile):
    test.top_filename = 't/t_fourstate_rtmd_trace.v'
    test.compile(make_main=False,
                 make_top_shell=False,
                 verilator_flags2=[
                     '--binary', '--fourstate', '-Wno-FUTURE', '--trace-' + profile,
                     '--trace-structs', '--output-split-cfuncs', '1', '--debug-check'
                 ])
    test.execute()
    expected = histories()
    widths = {name: len(rows[0][1]) for name, rows in expected.items()}
    proof = {'profile': profile, 'histories': expected, 'finish_time_ps': 44}
    if profile == 'saif':
        contents = Path(test.trace_filename).read_text()
        if not re.search(r'\(DURATION 44\)', contents):
            test.error('RTMD SAIF duration differs')
        actual = saif_records(contents)
        checked = 0
        for name, rows in expected.items():
            for bit in range(widths[name]):
                key = name + (f'[{bit}]' if widths[name] > 1 else '')
                wanted = dict.fromkeys(('T0', 'T1', 'TX', 'TZ', 'TB', 'TC'), 0)
                previous = '0'
                for index, (start, value) in enumerate(rows):
                    char = value[-1 - bit]
                    end = rows[index + 1][0] if index + 1 < len(rows) else 44
                    wanted['T' + char.upper()] += end - start
                    wanted['TC'] += int(char != previous)
                    previous = char
                if actual.get(key) != wanted:
                    test.error(f'RTMD SAIF {key}: {actual.get(key)}, expected {wanted}')
                checked += 1
        proof['bit_records_checked'] = checked
    elif profile == 'fst':
        proof['fst_audit'] = check_fst(test, test.trace_filename, expected, widths)
    else:
        check_vcd(test, test.trace_filename, expected, widths)
        decls = declarations(Path(test.trace_filename).read_text())
        for width in WIDTHS:
            a, alias, opposite = [
                decls.get(f't.w{width}.{n}') for n in ('a', 'real_alias', 'opposite')
            ]
            if not all((a, alias, opposite)):
                test.error(f'Missing RTMD declarations at width {width}')
                continue
            if a['code'] != alias['code']:
                test.error(f'True alias has a different trace code at width {width}')
            if a['code'] == opposite['code']:
                test.error(f'Different XZ histories share a trace code at width {width}')
        proof['declarations'] = {name: decls.get(name) for name in expected}
    data = Path(test.trace_filename).read_bytes()
    proof['trace_sha256'] = hashlib.sha256(data).hexdigest()
    Path(test.obj_dir + '/rtmd_trace_proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(f'RTMD trace oracle: profile={profile} histories={len(expected)}')
    test.passes()
