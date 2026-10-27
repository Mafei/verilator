#!/usr/bin/env python3
# DESCRIPTION: Verilator: Repeated positional OUTPUT wire ports
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('linter')
base_dir = test.obj_dir
base_v_flags = test.v_flags.copy()
for profile in ('delay', 'strength', 'tristate', 'force'):
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    # Every profile has an independently generated new golden and an explicit cause.
    test.lint(verilator_flags2=[
        '--fourstate', '-Wno-FUTURE', '--timing', '--top-module', 't', '--Mdir', test.obj_dir
    ],
              v_flags2=['+define+PROBE_' + profile.upper()],
              fails=True,
              expect_filename=test.golden_filename.replace('.out', '_' + profile + '.out'))
test.obj_dir = base_dir
test.v_flags = base_v_flags
test.passes()
