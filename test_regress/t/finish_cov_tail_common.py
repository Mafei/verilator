# DESCRIPTION: Strict finish coverage runtime and raw source-span checks
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import os
from pathlib import Path
import re


# Raw C-record grammar follows the existing coverage_covergroup_common.py helper.
# Attribute names follow include/verilated_cov_key.h; no output is normalized.
def coverage_records(path):
    records = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.startswith('C '):
            continue
        match = re.fullmatch(r"C '(.*)' (\d+)", line)
        if not match:
            raise ValueError('Malformed raw coverage record')
        fields = {}
        for part in match[1].split('\x01'):
            if not part:
                continue
            key, separator, value = part.partition('\x02')
            if not separator or key in fields:
                raise ValueError('Malformed or duplicate raw coverage attribute')
            fields[key] = value
        records.append((fields, int(match[2])))
    if not records:
        raise ValueError('No raw coverage records')
    return records


def covered_lines(text):
    result = set()
    for piece in text.split(','):
        if not piece:
            continue
        if re.fullmatch(r'\d+', piece):
            result.add(int(piece))
        elif re.fullmatch(r'\d+-\d+', piece):
            first, last = map(int, piece.split('-'))
            if last < first:
                raise ValueError('Invalid coverage source range')
            result.update(range(first, last + 1))
        else:
            raise ValueError('Unsupported coverage source range')
    return result


def expectations(source, profile):
    lines = Path(source).read_text(encoding='utf-8').splitlines()

    def at(token):
        return next(i for i, line in enumerate(lines, 1) if token in line)

    if profile == 'tails':
        owned = [
            'COV_EXTRA_TASK_NORMAL_RETURN ticks=1 task_entries=1 task_returns=0 normal_tail=0',
            'COV_EXTRA_NORMAL ticks=1 task_entries=1 task_returns=1 normal_tail=1',
            'COV_EXTRA_BEFORE_FINISH ticks=4 outer=3 inner=1 task_entries=2 task_returns=1 normal_tail=1',
            'COV_EXTRA_FINAL ticks=4 outer=3 inner=1 task_entries=2 task_returns=1 normal_tail=1',
            '*-* All Finished *-*'
        ]
        points = [('always_prefix', 'v_line/t', 'block', at('always @(posedge clk)'),
                   [at('always @(posedge clk)'),
                    at('// COV_CLOCK_BODY_PREFIX')],
                   [at('// COV_NORMAL_CALLER_FALLTHROUGH'),
                    at('// COV_OUTER_SELECTED_PREFIX')], 4),
                  ('outer_selected', 'v_branch/t', 'if', at('if (ticks >= 2)'),
                   [at('if (ticks >= 2)'),
                    at('// COV_OUTER_SELECTED_PREFIX')], [at('// COV_INNER_SELECTED_PREFIX')], 3),
                  ('inner_selected', 'v_branch/t', 'if', at('if (ticks == 4)'), [
                      at('if (ticks == 4)'),
                      at('// COV_INNER_SELECTED_PREFIX'),
                      at('// COV_FINISHING_CALL_TRUE')
                  ], [], 1),
                  ('normal_return', 'v_branch/t', 'if', at('if (ticks == 1)'), [
                      at('if (ticks == 1)'),
                      at('// COV_NORMAL_CALL_FALSE'),
                      at('// COV_NORMAL_CALLER_FALLTHROUGH')
                  ], [], 1),
                  ('task_complete_group', 'v_line/t', 'block', at('task automatic maybe_finish'),
                   [at('task automatic maybe_finish'),
                    at('// COV_TASK_NORMAL_RETURN_TAIL')], [], 1)]
    elif profile == 'barrier':
        owned = [
            'COV_DELAY_ENTER entered=1 time=0', 'COV_DELAY_FINAL entered=1 time=1',
            '*-* All Finished *-*'
        ]
        points = [('outer_boundary_group', 'v_line/t', 'block', at('initial begin : outer'),
                   [at('initial begin : outer'),
                    at('// COV_DELAY_OUTER_PREFIX')], [], 0),
                  ('mixed_if_group', 'v_branch/t', 'if', at('if (arm)'), [
                      at('if (arm)'),
                      at('// COV_DELAY_FINISH_CONTAINER'),
                      at('// COV_DELAY_DEAD_SIBLING')
                  ], [], 0),
                  ('dead_user_cover', 'v_user/t', None, at('// COV_DELAY_DEAD_USER_COVER'), [], [],
                   0)]
    else:
        raise ValueError('Unknown finish coverage profile')
    return owned, points


def verify(source, runtime, coverage, profile):
    expected, points = expectations(source, profile)
    text = Path(runtime).read_text(encoding='utf-8')
    owned = [
        line for line in text.splitlines()
        if line.startswith(('COV_EXTRA_', 'COV_DELAY_')) or line == '*-* All Finished *-*'
    ]
    issues = []
    if owned != expected:
        issues.append('Exact runtime owned lines mismatch')
    if re.search(r'%Error|ERROR:|%Fatal|FAILED|Assertion|Segmentation fault|Internal Error|DEAD_',
                 text):
        issues.append('Unexpected runtime error or functional tail')
    rows = coverage_records(coverage)
    found = []
    for name, page, comment, decl_line, include, exclude, want in points:
        candidates = [(fields, count) for fields, count in rows
                      if Path(fields.get('f', '')).resolve() == Path(source).resolve()
                      and fields.get('page') == page and fields.get('l') == str(decl_line) and (
                          comment is None or fields.get('o') == comment)]
        if len(candidates) != 1:
            issues.append(name + ': missing or ambiguous point; no default zero')
            found.append({
                'name': name,
                'status': 'ORACLE_NOT_RESOLVED',
                'matches': len(candidates)
            })
            continue
        fields, count = candidates[0]
        span = covered_lines(fields.get('S', ''))
        span_ok = set(include).issubset(span) and not set(exclude).intersection(span)
        if not span_ok:
            issues.append(name + ': source span mismatch')
        if count != want:
            issues.append(name + ': count ' + str(count) + ' != ' + str(want))
        found.append({
            'name': name,
            'fields': fields,
            'span': sorted(span),
            'span_ok': span_ok,
            'actual': count,
            'expected': want
        })
    return {
        'runtime_owned': owned,
        'runtime_expected': expected,
        'points': found,
        'issues': issues
    }


def run_public(test, profile):
    timing = '--no-timing' if profile == 'tails' else '--timing'
    test.compile(make_top_shell=False,
                 make_main=False,
                 verilator_flags2=[
                     '--cc', '--exe', test.pli_filename, timing, '--coverage-line',
                     '--coverage-branch', '--coverage-user', '--assert', '--debug-check',
                     '--top-module', 't'
                 ])
    log = test.obj_dir + '/run.log'
    raw = test.obj_dir + '/coverage.dat'
    test.execute(logfile=log, all_run_flags=[raw], check_finished=True)
    checked = verify(test.top_filename, log, raw, profile)
    for issue in checked['issues']:
        test.error(issue)
    # Use the same existing coverage tool interface as t_finish_coverage.py.
    test.run(cmd=[
        os.environ['VERILATOR_ROOT'] + '/bin/verilator_coverage', '--write-info',
        test.obj_dir + '/coverage.info', raw
    ],
             logfile=test.obj_dir + '/coverage_tool.log',
             verilator_run=True)
