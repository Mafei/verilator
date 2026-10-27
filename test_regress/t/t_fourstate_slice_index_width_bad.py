#!/usr/bin/env python3
# DESCRIPTION: Verilator: Preserve diagnostics before index carry arithmetic
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
test.lint(fails=True, verilator_flags2=['--fourstate', '-Wno-FUTURE', '--debug-check'])
test.file_grep_count(test.compile_log_filename, r'^%Warning-', 6)
test.file_grep_count(test.compile_log_filename, r'^%Error', 1)
test.file_grep(test.compile_log_filename, r'^%Error: Exiting due to 6 warning\(s\)$')
test.file_grep_count(test.compile_log_filename, r'%Warning-WIDTHEXPAND:', 2)
test.file_grep_count(test.compile_log_filename, r'%Warning-WIDTHTRUNC:', 4)
test.file_grep_count(
    test.compile_log_filename,
    r'%Warning-WIDTHTRUNC: [^\n]*: Bit extraction of array\[3:1\] requires 2 bit index, not 33 bits\.',
    1)
test.file_grep_count(test.compile_log_filename, r'requires 7 bit index, not 4 bits\.', 2)
test.file_grep_count(test.compile_log_filename, r'requires 7 bit index, not 64 bits\.', 3)
test.passes()
