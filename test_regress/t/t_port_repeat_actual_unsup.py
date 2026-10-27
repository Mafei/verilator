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
# Generate only the new golden with the actual reviewed compiler; then replay updatesOFF.
test.lint(verilator_flags2=['--fourstate', '-Wno-FUTURE', '--top-module', 't'],
          fails=True,
          expect_filename=test.golden_filename)

# These guard paths do not assert an observed compiler defect. The original formal
# remains unsplit until deferred cleanup; every source Pin must retain its audit.
base_dir = test.obj_dir
base_v_flags = test.v_flags.copy()
profiles = (('second_selected', 'PROBE_SECOND_SELECTED'), ('later_second', 'PROBE_LATER_SECOND'),
            ('nc_second', 'PROBE_NC_SECOND'))
for profile, define in profiles:
    test.obj_dir = base_dir + '/' + profile
    test.mkdir_ok(test.obj_dir)
    test.v_flags = base_v_flags.copy()
    test.lint(verilator_flags2=[
        '--fourstate', '-Wno-FUTURE', '--top-module', 't', '--Mdir', test.obj_dir
    ],
              v_flags2=['+define+' + define],
              fails=True,
              expect_filename=test.golden_filename.replace('.out', '_' + profile + '.out'))
    # Require the intended typed boundary as well as complete golden comparison.
    test.file_grep_count(
        test.obj_dir + '/vlt_compile.log',
        r'^%Error-UNSUPPORTED:.*Unsupported: Repeated OUTPUT ports require whole '
        r'plain four-state actual wires of matching width\.', 1)
    test.file_grep_not(test.obj_dir + '/vlt_compile.log',
                       r'Internal Error|Segmentation fault|Assertion .*failed')
test.obj_dir = base_dir
test.v_flags = base_v_flags
test.passes()
