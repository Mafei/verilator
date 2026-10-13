#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Validate every matrix report and complete selected-signal VCD histories from literal expectations."""
import argparse
import hashlib
import json
from pathlib import Path
import re

LANES = {'u7d': (7, 0, 0), 'u7a': (7, 1, 1),
         'u33d': (33, 0, 0), 'u33a': (33, 1, 1),
         'u65d': (65, 0, 0), 'u65a': (65, 1, 1)}
COUNTS = [3, 6, 9, 12, 15, 19, 23, 27, 31, 34, 38, 42, 48, 53]
REPORT = re.compile(r'^ARRAY_TMP W=(\d+) UP=([01]) PACKUP=([01]) phase=(\d+) '
                    r'first=([01xz]+) middle=([01xz]+) last=([01xz]+) '
                    r'side=(\d+) checks=(\d+)$')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patterns(width):
    return {'zero': '0' * width, 'one': '1' * width, 'x': 'x' * width, 'z': 'z' * width,
            'mixed': '10xz01'.rjust(width, '0'),
            'first': format(0x11, '0' + str(width) + 'b'),
            'middle': format(0x22, '0' + str(width) + 'b'),
            'last': format(0x33, '0' + str(width) + 'b')}


def report_expected(width, phase):
    p = patterns(width)
    triples = [('first', 'middle', 'last'), ('x', 'z', 'one'), ('mixed', 'zero', 'zero'),
               ('zero', 'zero', 'zero'), ('zero', 'z', 'zero'),
               ('zero', 'zero', 'zero'), ('zero', 'zero', 'zero'),
               ('zero', 'zero', 'zero'), ('zero', 'zero', 'zero'),
               ('x', 'z', 'mixed'), ('mixed', 'zero', 'zero'),
               ('z', 'zero', 'zero'), ('mixed', 'zero', 'zero'), ('mixed', 'zero', 'zero')]
    return {'words': [p[v] for v in triples[phase]],
            'side_effects': 0 if phase < 5 else (4 if phase < 10 else 1),
            'checks': COUNTS[phase]}


def expected_histories():
    result = {}
    for lane, (width, _, _) in LANES.items():
        p = patterns(width)
        histories = {
            'first_word': [(0, 'first'), (1, 'x'), (2, 'mixed'), (3, 'zero'),
                           (10, 'x'), (11, 'mixed'), (12, 'z'), (13, 'zero'), (14, 'mixed')],
            'middle_word': [(0, 'middle'), (1, 'z'), (2, 'zero'), (4, 'z'),
                            (5, 'zero'), (10, 'z'), (11, 'zero')],
            'last_word': [(0, 'last'), (1, 'one'), (2, 'zero'), (10, 'mixed'), (11, 'zero')],
        }
        for name, changes in histories.items():
            result['t.' + lane + '.' + name] = {'width': width,
                                               'changes': [[t, p[v]] for t, v in changes]}
        counter = [(0, 0), (1, 3), (2, 6), (3, 9), (4, 12), (5, 15), (6, 19),
                   (7, 23), (8, 27), (9, 31), (11, 34), (12, 38), (13, 42),
                   (14, 44), (15, 53)]
        result['t.' + lane + '.checks'] = {
            'width': 32, 'changes': [[t, format(v, '032b')] for t, v in counter]}
        result['t.' + lane + '.done'] = {'width': 1, 'changes': [[0, '0'], [15, '1']]}
    return result


def parse_vcd(path, expected, final_time=15):
    trace = path.read_text()
    assert re.search(r'\$timescale\s+1ps\s+\$end', trace), 'VCD time precision is not 1ps'
    scopes = []
    signals = {}
    actual = {name: [] for name in expected}
    time = 0
    last_time = 0
    timescale = []
    for line in trace.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == '$timescale':
            timescale.append(line)
        elif parts[0] == '$scope':
            scopes.append(parts[2])
        elif parts[0] == '$upscope':
            scopes.pop()
        elif parts[0] == '$var':
            name = '.'.join([*scopes, parts[4]])
            if name in expected:
                assert int(parts[2]) == expected[name]['width'], name + ': VCD width differs'
                signals.setdefault(parts[3], []).append(name)
        elif line.startswith('#'):
            time = int(line[1:])
            assert time >= last_time, 'Non-monotonic VCD time'
            last_time = time
        elif line.startswith('b') and len(parts) == 2:
            token, code = parts[0][1:].lower(), parts[1]
            for name in signals.get(code, []):
                assert set(token) <= set('01xz'), 'Invalid four-state VCD token'
                width = expected[name]['width']
                assert len(token) <= width, name + ': VCD token is too wide'
                value = token.rjust(width, token[0] if token[0] in 'xz' else '0')
                actual[name].append([time, value])
        elif line[0].lower() in '01xz':
            for name in signals.get(line[1:], []):
                assert expected[name]['width'] == 1, name + ': scalar token for a vector'
                actual[name].append([time, line[0].lower()])
    declared = {name for values in signals.values() for name in values}
    assert declared == set(expected), 'Expected VCD signals are missing'
    assert last_time == final_time, 'VCD did not reach the final fixture time'
    for name, value in expected.items():
        assert actual[name] == value['changes'], name + ': complete history differs'
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--vcd', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    process_records = []
    for path in sorted(args.evidence.glob('*.finished.json')):
        record = json.loads(path.read_text())
        assert record['actual_exit'] == 0 and record['raw_wait_status'] == 0
        log = Path(record['log'])
        assert log.stat().st_size == record['log_bytes']
        assert digest(log) == record['log_sha256']
        process_records.append({'path': str(path), 'pid': record['pid'], 'raw_wait_status': 0,
                                'log_sha256': record['log_sha256']})
    assert len(process_records) in (2, 3), 'Expected complete compile/run or compile/build/run receipts'
    assert args.log == args.evidence / 'run.log'
    reports = {}
    for line in args.log.read_text().splitlines():
        match = REPORT.fullmatch(line)
        if not match:
            assert not line.startswith('ARRAY_TMP'), 'Malformed matrix report'
            continue
        width, up, packup, phase = map(int, match.groups()[:4])
        assert 0 <= phase < 14
        key = (width, up, packup, phase)
        assert key not in reports, 'Duplicate matrix report'
        value = report_expected(width, phase)
        words = list(match.groups()[4:7])
        assert words == value['words'], str(key) + ': literal words differ'
        assert int(match[8]) == value['side_effects'], str(key) + ': side effects differ'
        assert int(match[9]) == value['checks'], str(key) + ': assertion count differs'
        reports[key] = {'words': words, 'side_effects': int(match[8]), 'checks': int(match[9])}
    required = {(w, u, p, phase) for w, u, p in LANES.values() for phase in range(14)}
    assert set(reports) == required, 'Matrix reports are incomplete or unexpected'
    assert args.log.read_text().count('*-* All Finished *-*') == 1
    expected = expected_histories()
    histories = parse_vcd(args.vcd, expected)
    result = {'status': 'PASS_LITERAL_OUTPUT_AND_COMPLETE_HISTORIES', 'label': args.label,
              'lane_count': 6, 'assertions_per_lane': 53, 'assertions_total': 318,
              'phase_reports': len(reports), 'complete_signal_histories': len(histories),
              'complete_history_records': sum(len(v) for v in histories.values()),
              'expected_histories': expected, 'actual_histories': histories,
              'reports': {'/'.join(map(str, k)): v for k, v in sorted(reports.items())},
              'process_receipts': process_records,
              'physical_outputs': {str(p): {'bytes': p.stat().st_size, 'sha256': digest(p)}
                                   for p in (args.log, args.vcd)},
              'normative_ieee_claim': False,
              'active_region_oracle': False,
              'normalizations': 'Only VCD omitted leading bits are expanded according to its four-state token; no transitions or repeated records are removed.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'label', 'assertions_total',
                     'phase_reports', 'complete_signal_histories', 'complete_history_records')}))


if __name__ == '__main__':
    main()
