#!/usr/bin/env python3
# DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import json
import re
import vltest_bootstrap

test.scenarios('vlt')

# Frozen expected state lines; raw simulator finish/statistics remain in run.log.
checks = (
    ('p0_a13_left', '0000000000000'),
    ('p0_a13_right', '0000000000000'),
    ('p0_b13_left', '1111111111111'),
    ('p0_b13_right', '1111111111111'),
    ('p0_a31_left', '0000000000000000000000000000000'),
    ('p0_a31_right', '0000000000000000000000000000000'),
    ('p0_b31_left', '1111111111111111111111111111111'),
    ('p0_b31_right', '1111111111111111111111111111111'),
    ('p0_a33_left', '000000000000000000000000000000000'),
    ('p0_a33_right', '000000000000000000000000000000000'),
    ('p0_b33_left', '111111111111111111111111111111111'),
    ('p0_b33_right', '111111111111111111111111111111111'),
    ('p0_unique33', '000000000000000000000000000000000'),
    ('p1_a13_left', '1111111111111'),
    ('p1_a13_right', '1111111111111'),
    ('p1_b13_left', '0000000000000'),
    ('p1_b13_right', '0000000000000'),
    ('p1_a31_left', '1111111111111111111111111111111'),
    ('p1_a31_right', '1111111111111111111111111111111'),
    ('p1_b31_left', '0000000000000000000000000000000'),
    ('p1_b31_right', '0000000000000000000000000000000'),
    ('p1_a33_left', '111111111111111111111111111111111'),
    ('p1_a33_right', '111111111111111111111111111111111'),
    ('p1_b33_left', '000000000000000000000000000000000'),
    ('p1_b33_right', '000000000000000000000000000000000'),
    ('p1_unique33', '111111111111111111111111111111111'),
    ('p2_a13_left', 'xxxxxxxxxxxxx'),
    ('p2_a13_right', 'xxxxxxxxxxxxx'),
    ('p2_b13_left', 'zzzzzzzzzzzzz'),
    ('p2_b13_right', 'zzzzzzzzzzzzz'),
    ('p2_a31_left', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p2_a31_right', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p2_b31_left', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p2_b31_right', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p2_a33_left', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p2_a33_right', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p2_b33_left', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p2_b33_right', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p2_unique33', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p3_a13_left', 'zzzzzzzzzzzzz'),
    ('p3_a13_right', 'zzzzzzzzzzzzz'),
    ('p3_b13_left', 'xxxxxxxxxxxxx'),
    ('p3_b13_right', 'xxxxxxxxxxxxx'),
    ('p3_a31_left', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p3_a31_right', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p3_b31_left', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p3_b31_right', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p3_a33_left', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p3_a33_right', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p3_b33_left', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p3_b33_right', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'),
    ('p3_unique33', 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
    ('p4_a13_left', '10xz01zx10xz0'),
    ('p4_a13_right', '10xz01zx10xz0'),
    ('p4_b13_left', '01zx10xz01zx1'),
    ('p4_b13_right', '01zx10xz01zx1'),
    ('p4_a31_left', '10xz01zx10xz01zx10xz01zx10xz01z'),
    ('p4_a31_right', '10xz01zx10xz01zx10xz01zx10xz01z'),
    ('p4_b31_left', '01zx10xz01zx10xz01zx10xz01zx10x'),
    ('p4_b31_right', '01zx10xz01zx10xz01zx10xz01zx10x'),
    ('p4_a33_left', '10xz01zx10xz01zx10xz01zx10xz01zx1'),
    ('p4_a33_right', '10xz01zx10xz01zx10xz01zx10xz01zx1'),
    ('p4_b33_left', '01zx10xz01zx10xz01zx10xz01zx10xz0'),
    ('p4_b33_right', '01zx10xz01zx10xz01zx10xz01zx10xz0'),
    ('p4_unique33', '1000000000000000xz111111111111111'),
    ('p4_a13_left_bit18', '1'),
    ('p4_a13_left_bit6', '0'),
    ('p4_a13_right_bit18', '1'),
    ('p4_a13_right_bit6', '0'),
    ('p4_a31_left_bit4', '1'),
    ('p4_a31_left_bit34', 'z'),
    ('p4_a31_right_bit34', '1'),
    ('p4_a31_right_bit4', 'z'),
    ('p4_a33_left_bit40', '1'),
    ('p4_a33_left_bit8', '1'),
    ('p4_a33_right_bit8', '1'),
    ('p4_a33_right_bit40', '1'),
    ('p5_a13_left', '1000000000000'),
    ('p5_a13_right', '1000000000000'),
    ('p5_b13_left', '0000000000001'),
    ('p5_b13_right', '0000000000001'),
    ('p5_a31_left', '1000000000000000000000000000000'),
    ('p5_a31_right', '1000000000000000000000000000000'),
    ('p5_b31_left', '0000000000000000000000000000001'),
    ('p5_b31_right', '0000000000000000000000000000001'),
    ('p5_a33_left', '100000000000000000000000000000000'),
    ('p5_a33_right', '100000000000000000000000000000000'),
    ('p5_b33_left', '000000000000000000000000000000001'),
    ('p5_b33_right', '000000000000000000000000000000001'),
    ('p5_unique33', '000000000000000000000000000000001'),
    ('p5_a13_left_bit18', '1'),
    ('p5_a13_left_bit6', '0'),
    ('p5_a13_right_bit18', '1'),
    ('p5_a13_right_bit6', '0'),
    ('p5_a31_left_bit4', '1'),
    ('p5_a31_left_bit34', '0'),
    ('p5_a31_right_bit34', '1'),
    ('p5_a31_right_bit4', '0'),
    ('p5_a33_left_bit40', '1'),
    ('p5_a33_left_bit8', '0'),
    ('p5_a33_right_bit8', '1'),
    ('p5_a33_right_bit40', '0'),
)

flags = [
    '--binary', '--fourstate', '--debug-check', '-Wno-FUTURE', '--top-module', 't', '--Mdir',
    test.obj_dir, '-j', '1', '-MAKEFLAGS', 'VM_PARALLEL_BUILDS=1', '--dumpi-tree', '6',
    '--dumpi-tree-json', '6', '--no-json-ids'
]
test.compile(make_top_shell=False, make_main=False, verilator_flags2=flags)
test.file_grep_not(test.obj_dir + '/vlt_compile.log', r'%Warning-|%Error|fatal error:|warning:')

# The primary linkdot snapshot is before Param cloning and before Inst deletes Pins.
# Later linkdot snapshots may contain no Pins; retain all raw dumps for diagnosis.
text_slots = []
for filename in test.glob_some(test.obj_dir + '/*_linkdot.tree'):
    for line in test.file_contents(filename).splitlines():
        if '[REPEATED_OUTPUT_FANOUT]' in line:
            match = re.search(r'\bportSlot=(\d+)\b', line)
            if not match or not re.search(r'\bPIN\b', line):
                test.error('Repeated OUTPUT pin text dump lacks a formal slot')
            else:
                text_slots.append(int(match.group(1)))
if sorted(text_slots) != [1] * 6 + [2] * 6:
    test.error('Repeated OUTPUT text dump lost or duplicated positional identities')

json_slots = []


def inspect_json(value):
    if isinstance(value, dict):
        if value.get('repeatedOutputFanout') is True:
            if value.get('type') != 'PIN' or value.get('resolvedPortSlot') not in (1, 2):
                test.error('Repeated OUTPUT pin JSON lacks a formal slot')
            else:
                json_slots.append(value['resolvedPortSlot'])
        for child in value.values():
            inspect_json(child)
    elif isinstance(value, list):
        for child in value:
            inspect_json(child)


for filename in test.glob_some(test.obj_dir + '/*_linkdot.tree.json'):
    inspect_json(json.loads(test.file_contents(filename)))
if sorted(json_slots) != [1] * 6 + [2] * 6:
    test.error('Repeated OUTPUT JSON dump lost or duplicated positional identities')

log = test.obj_dir + '/run.log'
test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
test.file_grep_not(
    log, r'%Error|ERROR:|%Fatal|FAILED|Assertion|assertion|Segmentation fault|Internal Error')
expected = [
    'PORT_REPEAT_OUTPUT_CHECK n=' + str(index) + ' label=' + label + ' got=' + value
    for index, (label, value) in enumerate(checks, 1)
]
expected += ['PORT_REPEAT_OUTPUT checks=102', '*-* All Finished *-*']
owned = [
    line for line in test.file_contents(log).splitlines()
    if line.startswith('PORT_REPEAT_OUTPUT') or line == '*-* All Finished *-*'
]
if owned != expected:
    test.error('Missing, duplicated, reordered or incorrect repeated OUTPUT state output')
test.file_grep_count(log, r'^PORT_REPEAT_OUTPUT_CHECK ', 102)
test.file_grep_count(log, r'^PORT_REPEAT_OUTPUT checks=102$', 1)
test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
test.passes()
