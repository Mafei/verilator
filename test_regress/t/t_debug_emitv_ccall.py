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

base_dir = test.obj_dir
test.mkdir_ok(base_dir)
for profile in ('two', 'four'):
    test.mkdir_ok(base_dir + '/' + profile)
    flags = ['--top-module', 't']
    if profile == 'four':
        flags += ['--fourstate', '-Wno-FUTURE']

    # Generate the post-task diagnostic without making or running a model.
    # Synthetic C ABI argTypes remain outside this visible-expression check.
    test.obj_dir = base_dir + '/' + profile + '/dump'
    test.mkdir_ok(test.obj_dir)
    test.compile(make_top_shell=False,
                 make_main=False,
                 verilator_make_gmake=False,
                 verilator_flags2=[
                     *flags, '--cc', '--Mdir', test.obj_dir, '--dumpi-tree', '9',
                     '--dumpi-V3EmitV', '9', '--debug-emitv'
                 ])
    dump = test.glob_one(test.obj_dir + '/' + test.vm_prefix + '_*_task.tree.v')
    wrapper = r'__Vdpiimwrap_[\w.]*'
    left = r'(?:t\.)?left'
    right = r'(?:t\.)?right'
    result = r'[\w.]*ccall_pair[\w.]*'
    test.file_grep(
        dump,
        wrapper + r'ccall_pair[\w.]*\(\s*' + left + r',\s*' + right + r',\s*' + result + r'\)')
    test.file_grep(
        dump,
        wrapper + r'ccall_pair[\w.]*\(\s*' + right + r',\s*' + left + r',\s*' + result + r'\)')
    context = wrapper + r'ccall_context_pair[\w.]*'
    test.file_grep(
        dump, context + r'\(\s*\$_CEXPR\("[^"]*t_debug_emitv_ccall\.v"\)\s*,\s*' +
        r"32's?h[0-9a-fA-F]+,\s*" + left + r',\s*' + right +
        r',\s*[\w.]*ccall_context_pair[\w.]*\)')
    test.file_grep_not(dump, context + r'\(\s*,')
    test.file_grep_not(dump, context + r'\([^;]*,\s*,')
    test.file_grep(dump,
                   wrapper + r'ccall_single[\w.]*\(\s*' + left + r',\s*[\w.]*ccall_single[\w.]*\)')
    test.file_grep(dump, wrapper + r'ccall_empty[\w.]*\(\s*[\w.]*ccall_empty[\w.]*\)')
    # Unlike a zero-input function, this task has no lowered return argument.
    test.file_grep(dump, wrapper + r'ccall_empty_task[\w.]*\(\s*\)')

    # Keep the diagnostic files distinct from the executable model build.
    test.obj_dir = base_dir + '/' + profile + '/run'
    test.mkdir_ok(test.obj_dir)
    test.compile(make_top_shell=False,
                 make_main=False,
                 v_flags2=['t/t_debug_emitv_ccall_c.cpp'],
                 verilator_flags2=[
                     *flags, '--binary', '--main-top-name', 'TOP', '--no-timing', '--Mdir',
                     test.obj_dir, '-j', '1'
                 ])
    log = test.obj_dir + '/run.log'
    test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=True)
    test.file_grep(log, r'^EmitV CCall runtime checks: (\d+)$', 258)
    test.file_grep_count(log, r'^\*-\* All Finished \*-\*$', 1)
    test.file_grep_not(log, r'%Error|ERROR:')

test.obj_dir = base_dir
test.passes()
