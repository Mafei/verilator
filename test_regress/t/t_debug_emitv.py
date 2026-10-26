#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2024 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
import hashlib
import json
from pathlib import Path

test.scenarios("vlt")

test.lint(
    # We also have dump-tree turned on, so hit a lot of AstNode*::dump() functions
    # Likewise XML
    v_flags=[
        "--lint-only",
        # --Wno-COVERIGN: cg_trans uses a goto-repetition transition bin ([->N]); the count is
        # unsupported (dropped) but the bin is still created with a non-NONE VTransRepType, which
        # is what exercises VTransRepType::ascii() and AstCoverTransItem::dump()'s repType arm.
        "--Wno-COVERIGN",
        "--timing",
        "--dumpi-tree 9 --dumpi-V3EmitV 9 --debug-emitv",  # Dev coverage of the V3EmitV code
        "--dump-graph --dumpi-tree-json 9 --no-json-ids"
    ])

output_vs = test.glob_some(test.obj_dir + "/" + test.vm_prefix + "_*_width.tree.v")

total_output_bytes = sum(Path(path).stat().st_size for path in output_vs)
if total_output_bytes > 128 * 1024:
    test.error('Debug emitv evidence exceeds the public fixture byte budget')
for output_v in output_vs:
    raw = Path(output_v).read_bytes()
    print('DEBUG_EMITV_RAW ' + json.dumps({
        'path': output_v,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'contents_latin1': raw.decode('latin-1')
    }))
    test.files_identical(output_v, test.golden_filename, normalize_enum_hash=True)

if test.verbose:
    # Print if that the output Verilog is clean
    # TODO not yet round-trip clean
    test.run(
        cmd=[
            os.environ["VERILATOR_ROOT"] + "/bin/verilator",
            "--lint-only",
            output_vs[0],
        ],
        logfile=test.obj_dir + "/sim_roundtrip.log",
        fails=True,
        verilator_run=True,
    )

test.passes()
