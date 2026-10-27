#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run timing and C++14 no-timing models using only a relocated installation."""
import os
import pathlib
import shlex
import subprocess
import sys

compiler = str(pathlib.Path(sys.argv[1]).resolve())
work = pathlib.Path(sys.argv[2]).resolve()
work.mkdir(parents=True, exist_ok=True)
source = pathlib.Path(__file__).resolve().parents[2] / 'test_regress/t/t_fourstate_portable.v'
env = os.environ.copy()
env.pop('VERILATOR_ROOT', None)
env.pop('CPLUS_INCLUDE_PATH', None)
link_flags = ['-LDFLAGS', '-static-libstdc++ -static-libgcc'] if sys.platform.startswith('linux') else []
subprocess.run([compiler, '--version'], check=True, env=env)
subprocess.run([compiler, '--binary', '--fourstate', '-Wno-FUTURE', '--top-module', 't', '--Mdir', str(work / 'obj_dir'), '-j', '2', *link_flags, str(source)], check=True, cwd=work, env=env)
model = work / 'obj_dir/Vt'
passed = subprocess.run([str(model)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
print(passed.stdout)
assert passed.returncode == 0 and '*-* All Finished *-*' in passed.stdout, passed.returncode
subprocess.run([compiler, '--binary', '--fourstate', '-Wno-FUTURE', '--top-module', 't', '-GREJECT_X=1', '--Mdir', str(work / 'reject_obj'), '-j', '2', *link_flags, str(source)], check=True, cwd=work, env=env)
rejected = subprocess.run([str(work / 'reject_obj/Vt')], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
print(rejected.stdout)
assert rejected.returncode != 0 and 'FOURSTATE_UNKNOWN_REJECTED' in rejected.stdout, rejected.returncode
runtime_source = pathlib.Path(__file__).with_name('runtime_cxx14.sv')
subprocess.run([
    compiler, '--binary', '--no-timing', '--fourstate', '-Wno-FUTURE', '--top-module',
    'runtime_cxx14', '--Mdir', str(work / 'cxx14_obj'), '-j', '1', '-CFLAGS', '-std=c++14',
    *link_flags, str(runtime_source)
], check=True, cwd=work, env=env)
runtime_model = work / 'cxx14_obj/Vruntime_cxx14'
runtime = subprocess.run([str(runtime_model)], text=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, env=env)
print(runtime.stdout)
assert runtime.returncode == 0 and runtime.stdout.splitlines().count(
    'CXX14_NO_TIMING_FOURSTATE_RUNTIME_PASS') == 1, runtime.returncode
runtime_root = pathlib.Path(
    subprocess.check_output([compiler, '--getenv', 'VERILATOR_ROOT'], text=True, env=env).strip())
insert_model = work / 'runtime_insert'
subprocess.run([
    *shlex.split(env.get('CXX', 'c++')), '-std=c++14', '-O1', '-I',
    str(runtime_root / 'include'),
    str(pathlib.Path(__file__).with_name('runtime_insert.cpp')),
    *(['-static-libstdc++', '-static-libgcc'] if sys.platform.startswith('linux') else []), '-o',
    str(insert_model)
],
               check=True,
               cwd=work,
               env=env)
insert = subprocess.run([str(insert_model)],
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        env=env)
print(insert.stdout)
assert insert.returncode == 0 and insert.stdout.splitlines() == ['CXX14_INSERT_PASS checks=3296'
                                                                 ], insert.returncode
if sys.platform.startswith('linux'):
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('check_elf.py')), str(model)], check=True)
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('check_elf.py')),
                    str(runtime_model)], check=True)
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('check_elf.py')),
                    str(insert_model)], check=True)
