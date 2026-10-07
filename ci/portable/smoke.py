#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Compile and run a real timing model using only a relocated installation."""
import os
import pathlib
import subprocess
import sys

compiler = str(pathlib.Path(sys.argv[1]).resolve())
work = pathlib.Path(sys.argv[2]).resolve()
work.mkdir(parents=True, exist_ok=True)
source = pathlib.Path(__file__).resolve().parents[2] / 'test_regress/t/t_fourstate_portable.v'
env = os.environ.copy()
env.pop('VERILATOR_ROOT', None)
subprocess.run([compiler, '--version'], check=True, env=env)
subprocess.run([compiler, '--binary', '--fourstate', '-Wno-FUTURE', '--top-module', 't', '--Mdir', str(work / 'obj_dir'), '-j', '2', str(source)], check=True, cwd=work, env=env)
model = work / 'obj_dir/Vt'
passed = subprocess.run([str(model)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
print(passed.stdout)
assert passed.returncode == 0 and '*-* All Finished *-*' in passed.stdout, passed.returncode
rejected = subprocess.run([str(model), '+reject_x'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
print(rejected.stdout)
assert rejected.returncode != 0 and 'FOURSTATE_UNKNOWN_REJECTED' in rejected.stdout, rejected.returncode
if sys.platform.startswith('linux'):
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('check_elf.py')), str(model)], check=True)
