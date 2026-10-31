#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Check clocking output skew and passive sources from the public fixture's VCD."""

import hashlib
import json
import re
import subprocess
from pathlib import Path


def require(condition, message):
    """Keep incomplete or malformed waveform evidence fatal."""
    if not condition:
        raise ValueError(message)


def parse_wave(data):
    """Read stable values after each timestamp, preserving VCD identifier aliases."""
    text = data.decode('ascii')
    require(re.search(r'\$timescale\s+1ps\s+\$end', text), 'clocking_timescale')
    scopes, names, values, frames = [], {}, {}, {}
    current = 0
    header = True
    for line in text.splitlines():
        words = line.split()
        if not words:
            continue
        token = words[0]
        if header:
            if token == '$scope':
                scopes.append(words[2])
            elif token == '$upscope':
                scopes.pop()
            elif token == '$var':
                name = '.'.join(scopes + [words[4]])
                require(name not in names, 'clocking_duplicate_signal')
                names[name] = words[3]
            elif token == '$enddefinitions':
                require(not scopes, 'clocking_unclosed_scope')
                header = False
            continue
        if token.startswith('#'):
            frames[current] = dict(values)
            next_time = int(token[1:])
            require(next_time >= current, 'clocking_time_reversed')
            current = next_time
        elif token[0] in 'bB':
            require(len(words) == 2, 'clocking_invalid_vector')
            values[words[1]] = token[1:].lower()
        elif token[0] in '01xXzZ':
            values[token[1:]] = token[0].lower()
        else:
            require(token in ('$dumpvars', '$end'), 'clocking_invalid_record')
    require(not header, 'clocking_missing_header')
    frames[current] = dict(values)
    require(current >= 86002, 'clocking_truncated_wave')
    return names, frames


def output_values(value):
    """Compute the four independent legal output routes, including concatenations."""
    concat = value ^ 0x56d3
    direct = (value + 0x72d) & 0x7fff
    return {
        't.flat_bus': value,
        't.concat_hi': concat >> 8,
        't.concat_lo': concat & 255,
        't.task_bus': (~value) & 0x7fff,
        't.direct_hi': direct >> 8,
        't.direct_lo': direct & 255
    }


def verify(data):  # pylint: disable=too-many-locals
    """Check event-time old values, exact 1ps updates, and unchanged passive inputs."""
    names, frames = parse_wave(data)
    checks = 0

    def compare(time, signal, expected):
        nonlocal checks
        require(time in frames and signal in names, 'clocking_missing_observation')
        raw = frames[time].get(names[signal], '')
        require(raw and not set(raw).difference('01'), 'clocking_unknown_value')
        require(int(raw, 2) == expected, f'clocking_value time={time} signal={signal}')
        checks += 1

    for cycle in range(8):
        value = (cycle * 5281 + 5779) & 0x7fff
        event = 15000 + cycle * 10000
        for time in (event + 1, event + 1002):
            for signal, expected in output_values(value).items():
                compare(time, signal, expected)
        if cycle:
            previous = ((cycle - 1) * 5281 + 5779) & 0x7fff
            for signal, expected in output_values(previous).items():
                compare(event, signal, expected)
        a_value = (cycle * 317 + 53) & 0x7fff
        b_value = (cycle * 521 + 109) & 0x7fff
        pattern = (cycle * 911 + 73) & 0x7fff
        concat = (cycle * 701 + 211) & 0x7fff
        sources = {
            't.a': a_value,
            't.b': b_value,
            't.pattern_hi': pattern >> 8,
            't.pattern_lo': pattern & 255,
            't.passive_hi': concat >> 8,
            't.passive_lo': concat & 255,
            't.arithmetic.bus': (a_value + b_value) & 0x7fff,
            't.pattern_value.bus': pattern,
            't.independent_concat.bus': concat
        }
        begin = 10000 + cycle * 10000
        for time in frames:
            if begin <= time < begin + 10000:
                for signal, expected in sources.items():
                    compare(time, signal, expected)
    require(checks >= 426, 'clocking_incomplete_checks')
    return checks


def validate(root):
    """Recompute evidence without executing the compiler or models."""
    directory = root / 'test_regress/obj_vlt/t_clocking_port_connections'
    contents = {}
    for name in ('simx.vcd', 'vlt_sim.log'):
        path = directory / name
        require(path.is_file() and not path.is_symlink(), 'clocking_missing_regular_file')
        data = path.read_bytes()
        require(0 < len(data) <= 128 * 1024, 'clocking_evidence_size')
        contents[name] = data
    wave = contents['simx.vcd']
    log = contents['vlt_sim.log']
    require(
        log.count(b'settled cycle=') == 8 and b'*-* All Finished *-*' in log,
        'clocking_incomplete_simulation')
    return {
        'schema': 'clocking-wave-v1',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'compiler_sha256': hashlib.sha256((root / 'bin/verilator_bin').read_bytes()).hexdigest(),
        'semantic_pass': True,
        'cycles': 8,
        'output_skew_ps': 1,
        'checks': verify(wave),
        'wave_sha256': hashlib.sha256(wave).hexdigest(),
        'sim_log_sha256': hashlib.sha256(log).hexdigest()
    }


def core_fields(report):
    """Whitelist typed evidence while rejecting false passes or missing observations."""
    keys = {
        'schema', 'head', 'compiler_sha256', 'semantic_pass', 'cycles', 'output_skew_ps', 'checks',
        'wave_sha256', 'sim_log_sha256'
    }
    require(
        set(report) == keys and report['schema'] == 'clocking-wave-v1'
        and report['semantic_pass'] is True, 'clocking_typed_schema')
    require(
        isinstance(report['head'], str) and re.fullmatch(r'[0-9a-f]{40}', report['head']),
        'clocking_typed_head')
    for name in ('compiler_sha256', 'wave_sha256', 'sim_log_sha256'):
        require(
            isinstance(report[name], str) and re.fullmatch(r'[0-9a-f]{64}', report[name]),
            'clocking_typed_hash')
    # JSON booleans must not count as integer checks or timing observations.
    # pylint: disable=unidiomatic-typecheck
    require(
        type(report['cycles']) is int and report['cycles'] == 8
        and type(report['output_skew_ps']) is int and report['output_skew_ps'] == 1
        and type(report['checks']) is int and 426 <= report['checks'] <= 20000,
        'clocking_typed_checks')
    # pylint: enable=unidiomatic-typecheck
    return dict(report)


def check(root):
    """Publish evidence only after all waveform checks complete."""
    report = core_fields(validate(root))
    (root / 'out').mkdir(exist_ok=True)
    (root / 'out/clocking-wave-evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    print('CLOCKING_WAVE_EVIDENCE ' + json.dumps(report, sort_keys=True))
    return report


if __name__ == '__main__':
    try:
        check(Path(__file__).resolve().parents[2])
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit('Invalid clocking waveform evidence: ' + str(error)) from error
