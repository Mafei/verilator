#!/usr/bin/env python3
# DESCRIPTION: Verilator: Independent event-controlled NBA controls
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Check complete physical VCD histories and phase output against independent literals."""
import hashlib
import re

COUNTS = {'capture': 38, 'unknown': 13, 'race': 20, 'tasks': 36, 'trigger': 24}


def payload(width, phase):
    # This literal digit sequence is independent of the SV case-based producer.
    return ''.join('01xz'[(bitno + phase) % 4] for bitno in range(width - 1, -1, -1))


def bits(width, value):
    return f'{value:0{width}b}'


def parse_vcd(path, wanted):
    widths, codes, histories, scopes = {}, {}, {}, []
    timestamp = 0
    for line in path.read_text().splitlines():
        line = line.strip()
        fields = line.split()
        if line.startswith('$scope'):
            scopes.append(fields[2])
        elif line.startswith('$upscope'):
            scopes.pop()
        elif line.startswith('$var'):
            name = '.'.join(scopes + [fields[4]])
            if name in wanted:
                widths[name] = int(fields[2])
                codes.setdefault(fields[3], []).append(name)
                histories[name] = []
        elif line.startswith('#'):
            timestamp = int(line[1:])
        elif fields and (line[0] in 'bB' or line[0] in '01xzXZ'):
            value, code = (fields[0][1:].lower(),
                           fields[1]) if line[0] in 'bB' else (line[0].lower(), line[1:].strip())
            for name in codes.get(code, []):
                fill = value[0] if value[0] in 'xz' else '0'
                value = value.rjust(widths[name], fill)
                if len(value) != widths[name]:
                    raise ValueError('VCD value width differs: ' + name)
                history = histories[name]
                if not history or history[-1][1] != value:
                    history.append((timestamp, value))
    if set(histories) != set(wanted):
        raise ValueError('Missing/duplicate expected VCD signal')
    return histories


def expected(name):
    result = {}
    if name == 'capture':
        for slot in range(1, 4):
            for label, width, offset in [('bank', 33, 0), ('hi', 33, 32), ('lo', 32, 0)]:
                result[f't.{label}{slot}'] = [(0, '0' * width)]
                for phase in range(4):
                    full = payload(65, phase + slot)
                    value = full[65 - offset - width:65 - offset]
                    result[f't.{label}{slot}'].append((2 * phase + 1, value))
        result['t.partial'] = [(0, '0' * 33)]
        result['t.ascending'] = [(0, '0' * 33)]
        for phase in range(4):
            result['t.partial'].append(
                (2 * phase + 1, '0' * 15 + payload(15, phase + 1) + '0' * 3))
            result['t.ascending'].append((2 * phase + 1, payload(33, phase + 1)))
        result['t.rearmed'] = [(0, '0' * 33)] + [(9 + 3 * phase, payload(33, phase))
                                                 for phase in range(3)]
    elif name == 'unknown':
        result = {f't.bank{slot}': [(0, bits(7, slot * 0x11))] for slot in range(1, 4)}
        result['t.partial'] = [(0, bits(15, 0x3535))]
        result['t.other'] = [(0, bits(7, 0x23)), (3, 'x01z101'), (6, 'z10x010')]
    elif name == 'tasks':
        for slot in range(1, 4):
            for label in ['bank', 'plain']:
                result[f't.{label}{slot}'] = [(0, '0' * 33)] + [
                    (3 + 4 * phase, payload(33, phase + slot)) for phase in range(3)
                ]
    elif name == 'trigger':
        result = {
            f't.count{slot}': [(0, bits(32, 0))] + [(1 + 2 * phase, bits(32, phase + 1))
                                                    for phase in range(4)]
            for slot in range(1, 4)
        }
    elif name == 'race':
        for label, reset in [('active_value', 0x11), ('nba_value', 0x22)]:
            result['t.' + label] = [(0, '0' * 7)]
            for phase in range(4):
                result['t.' + label] += [(3 * phase + 1, bits(7, reset)),
                                         (3 * phase + 2, 'z10x010' if phase % 2 else 'x01z101')]
        result['t.payload'] = [(0, '0' * 7)] + [
            (3 * phase + 1, 'z10x010' if phase % 2 else 'x01z101') for phase in range(4)
        ]
        result['t.nba_seen'] = [(0, '0' * 7), (2, bits(7, 0x22))]
    return result


# Keep each scenario's complete histories and phase/race checks together.
def check(name, wave, log):  # pylint: disable=too-many-locals
    golden = expected(name)
    actual = parse_vcd(wave, set(golden) | ({'t.active_seen'} if name == 'race' else set()))
    for signal, history in golden.items():
        if actual[signal] != history:
            raise ValueError(
                f'{name}: complete history differs: {signal}: {actual[signal]} != {history}')
    text = log.read_text()
    marker = {
        'capture': 'CONTROLS',
        'unknown': 'UNKNOWN',
        'race': 'RACE',
        'tasks': 'TASKS',
        'trigger': 'TRIGGER'
    }[name]
    if len(re.findall(rf'^EVENT_NBA_{marker}_PASS checks={COUNTS[name]}$', text, re.M)) != 1:
        raise ValueError('Missing/duplicate exact semantic pass count: ' + name)
    if name == 'capture':
        for phase in range(4):
            old_bank = '0' * 33 if phase == 0 else payload(33, phase)
            old_partial = '0' * 33 if phase == 0 else '0' * 15 + payload(15, phase) + '0' * 3
            bank = payload(33, phase + 1)
            partial = '0' * 15 + payload(15, phase + 1) + '0' * 3
            for prefix, time, bvalue, pvalue in [('ARM', 2 * phase + 1, old_bank, old_partial),
                                                 ('ACTIVE', 2 * phase + 1, old_bank, old_partial),
                                                 ('POST', 2 * phase + 1, bank, partial),
                                                 ('FINAL', 2 * phase + 2, bank, partial)]:
                line = f'{prefix} phase={phase} t={time} bank1={bvalue} partial={pvalue}'
                if text.splitlines().count(line) != 1:
                    raise ValueError('Exact phase observation differs: ' + line)
    if name == 'race':
        history = actual['t.active_seen']
        if not history or history[0] != (0, '0' * 7):
            raise ValueError('Active-race initial history differs')
        for timestamp, value in history[1:]:
            phase = (timestamp - 2) // 3
            if timestamp not in (2, 5, 8, 11) or value not in (bits(
                    7, 0x11), 'z10x010' if phase % 2 else 'x01z101'):
                raise ValueError('Active race outside legal timestamp/value set')
        for phase in range(4):
            value = 'z10x010' if phase % 2 else 'x01z101'
            pattern = rf'^RACE phase={phase} active_seen=({bits(7, 0x11)}|{value}) nba_seen={bits(7, 0x22)} final={value}$'
            if len(re.findall(pattern, text, re.M)) != 1:
                raise ValueError('Active race stdout outside its allowed set')
    return {
        'test': name,
        'signals': len(actual),
        'complete_histories': actual,
        'wave_bytes': wave.stat().st_size,
        'wave_sha256': hashlib.sha256(wave.read_bytes()).hexdigest(),
        'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
        'checks': COUNTS[name]
    }
