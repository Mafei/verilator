#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2024 Wilson Snyder
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')

test.lint(v_flags=['--lint-only', '--dumpi-tree 9 --dumpi-V3EmitV 9 --debug-emitv'])

output_v = test.glob_one(test.obj_dir + '/' + test.vm_prefix + '_*_widthcommit.tree.v')
test.file_grep(output_v, r'pair\(left,\s*right\)')
test.file_grep(output_v, r'pair\(right,\s*left\)')
test.file_grep(output_v, r'pair\(single\(left\),\s*pair\(\s*right,\s*left\)\)')
test.file_grep_count(output_v, r'defaults\(left,\s*32\x27sh11\)', 2)
test.file_grep(output_v, r'single\(right\)')
test.file_grep(output_v, r'empty\(\)')
test.file_grep(output_v, r'save\(left,\s*right,\s*result\)')

# Named and explicitly omitted arguments are retained before linking; both calls
# to defaults gain the same argument value at widthcommit.
output_cells = test.glob_one(test.obj_dir + '/' + test.vm_prefix + '_*_cells.tree.v')
test.file_grep(output_cells, r'pair\(\.second\(left\),\s*\.first\(right\)\)')
test.file_grep_count(output_cells, r'defaults\(left\)', 1)
test.file_grep_count(output_cells, r'defaults\(left, \)', 1)

test.passes()
