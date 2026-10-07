#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require an x86-64 ELF with a Rocky 8 compatible glibc symbol floor."""
import re
import subprocess
import sys

binary = sys.argv[1]
header = subprocess.check_output(['readelf', '-h', binary], text=True)
assert 'Advanced Micro Devices X86-64' in header, header
versions = subprocess.check_output(['readelf', '--version-info', binary], text=True)
required = sorted(set(re.findall(r'GLIBC_(\d+(?:\.\d+)+)', versions)), key=lambda v: tuple(map(int, v.split('.'))))
assert required and all(tuple(map(int, v.split('.'))) <= (2, 28) for v in required), required
libraries = subprocess.check_output(['ldd', binary], text=True)
assert 'not found' not in libraries, libraries
assert 'libstdc++.so' not in libraries and 'libgcc_s.so' not in libraries, libraries
print(header, libraries, 'Required GLIBC versions:', ', '.join(required))
