#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Record original branch behavior with a common scalar positive control."""
import json
import os
import pathlib
import re
import subprocess
import sys

compiler = pathlib.Path(sys.argv[1]).resolve()
work = pathlib.Path(sys.argv[2]).resolve()
work.mkdir(parents=True, exist_ok=True)
source = work / 'scalar.sv'
source.write_text('''module t;
  logic [6:0] value;
  bit choose = 0;
  initial begin
    #1;
    if (value !== 7'bxxxxxxx) $fatal(1, "initial X");
    value = 7'b10xz010;
    #1;
    if (value !== 7'b10xz010) $fatal(1, "scalar X/Z");
    choose = 1;
    value = choose ? 7'b0011101 : 7'b1110000;
    #1;
    if (value !== 7'b0011101) $fatal(1, "scalar ternary");
    $display("BASELINE_SCALAR_PASS");
    $finish;
  end
endmodule
''')
subprocess.run([str(compiler), '--binary', '--fourstate', '-Wno-FUTURE', '--top-module', 't', '--Mdir', str(work / 'scalar_obj'), '-j', '2', str(source)], check=True)
scalar = subprocess.run([str(work / 'scalar_obj/Vt')], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(scalar.stdout)
assert scalar.returncode == 0 and 'BASELINE_SCALAR_PASS' in scalar.stdout
probe = pathlib.Path('test_regress/t/t_fourstate_portable.v').resolve()
command = [str(compiler), '--binary', '--fourstate', '-Wno-FUTURE', '--top-module', 't', '--Mdir', str(work / 'aggregate_obj'), '-j', '2', str(probe)]
aggregate = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
pathlib.Path('out/baseline-aggregate.log').write_text(aggregate.stdout)
report = {'baseline': os.environ['PORTABLE_BASELINE'], 'scalar': 'pass', 'aggregate_compile_returncode': aggregate.returncode}
if os.environ['PORTABLE_BASELINE'] == 'feature':
    assert aggregate.returncode != 0 and re.search(r'Unsupported: (?:Operator|Variable of type)', aggregate.stdout), aggregate.stdout
    assert 'Internal Error' not in aggregate.stdout, aggregate.stdout
    report['aggregate'] = 'expected unsupported, matching the earlier four-state experiment'
else:
    assert aggregate.returncode == 0, aggregate.stdout
    execution = subprocess.run([str(work / 'aggregate_obj/Vt')], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(execution.stdout)
    assert execution.returncode == 0 and '*-* All Finished *-*' in execution.stdout
    report['aggregate'] = 'pass'
pathlib.Path('out/baseline-results.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
