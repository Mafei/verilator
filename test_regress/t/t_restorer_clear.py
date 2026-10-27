#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import os
import shlex
import vltest_bootstrap

test.scenarios('vlt')

binary = test.obj_dir + '/restorer_clear'
test.run(cmd=[
    os.environ['CXX'], '-std=c++14', '-Wall', '-Wextra', '-Werror', '-pedantic',
    '-I' + shlex.quote(os.environ['VERILATOR_ROOT'] + '/include'),
    shlex.quote(test.t_dir + '/t_restorer_clear.cpp'), '-o', shlex.quote(binary)
],
         logfile=test.obj_dir + '/compile.log')
test.run(cmd=[shlex.quote(binary)], logfile=test.obj_dir + '/run.log', check_finished=True)
test.file_grep(test.obj_dir + '/run.log', r'^RESTORER_CLEAR checks=33 failures=0$')

test.passes()
