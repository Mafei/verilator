#!/usr/bin/env python3
# DESCRIPTION: Verilator: Explicit four-state change-event initialization
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')

test.compile(
    make_top_shell=False,
    make_main=False,
    verilator_flags2=['--binary', '--fourstate', '--debug-check', '-j', '1', '-Wno-FUTURE'])
log = test.obj_dir + '/run.log'
test.execute(logfile=log, check_finished=True)
test.file_grep_not(log, r'%Error|ERROR:|%Fatal|FAILED|Assertion|Segmentation fault|Internal Error')
# These owned lines are exact and ordered; keep the raw simulator footer in run.log.
expected = [
    'FOURSTATE_SENSE_INIT p=0 default=xxxxxxxxxxxxx/0/0 x=xxxxxxxxxxxxx/0/0 z=zzzzzzzzzzzzz/0/0 known=0000000000000/0/0',
    'FOURSTATE_SENSE_INIT p=1 default=xxxxxxxxxxxxx/0/0 x=xxxxxxxxxxxxx/0/0 z=zzzzzzzzzzzzz/0/0 known=0000000000000/0/0',
    'FOURSTATE_SENSE_INIT p=2 default=zzzzzzzzzzzzz/1/1 x=1111111111111/1/1 z=xxxxxxxxxxxxx/1/1 known=0000001000000/1/1',
    'FOURSTATE_SENSE_INIT p=3 default=xxxxxxxxxxxxx/2/2 x=xxxxxxxxxxxxx/2/2 z=zzzzzzzzzzzzz/2/2 known=000000x000000/2/2',
    'FOURSTATE_SENSE_INIT p=4 default=xxxxxxxxxxxxx/2/2 x=xxxxxxxxxxxxx/2/2 z=zzzzzzzzzzzzz/2/2 known=000000x000000/2/2',
    'FOURSTATE_SENSE_INIT p=5 default=111111x111111/3/3 x=xxxxxxxxxxxxz/3/3 z=zzzzzz0zzzzzz/3/3 known=0000000000000/3/3',
    'FOURSTATE_SENSE_INIT p=6 default=1111110111111/4/4 x=xxxxxxxxxxxxx/4/4 z=zzzzzzzzzzzzz/4/4 known=1000000000000/4/4',
    'FOURSTATE_SENSE_INIT checks=84', '*-* All Finished *-*'
]
owned = [
    line for line in test.file_contents(log).splitlines()
    if line.startswith('FOURSTATE_SENSE_INIT') or line == '*-* All Finished *-*'
]
if owned != expected:
    test.error('Missing, duplicate, reordered or incorrect event initialization/count result')
test.file_grep_count(log, r'^FOURSTATE_SENSE_INIT p=', 7)
test.file_grep_count(log, r'^FOURSTATE_SENSE_INIT checks=84$', 1)
test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
test.passes()
