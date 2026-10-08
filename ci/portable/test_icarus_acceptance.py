#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Real native failure controls; fake model programs do not certify SV semantics."""
# Individual test names describe their bounded assertions.
# pylint: disable=missing-function-docstring

import base64
import copy
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import icarus_acceptance as acceptance

RECEIPTS = []


class AcceptanceTest(unittest.TestCase):  # pylint: disable=too-many-instance-attributes
    """Exercise production CLI, real exits/logs and isolated mutable controls."""

    @classmethod
    def setUpClass(cls):
        cls.contract = acceptance.load_contract(acceptance.CONTRACT)
        cls.upstream = Path(
            os.environ.get('ICARUS_FIXTURE_UPSTREAM',
                           acceptance.SOURCE_ROOT / '.ci-tools-src/icarus-official'))
        acceptance.verify_files(cls.contract, cls.upstream, download=True)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cache = self.root / 'upstream'
        for name in self.contract['files']:
            path = self.cache / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.upstream / name, path)
        self.repository = self.root / 'repository'
        for name in ('src/provenance.txt', 'include/verilated.h', 'bin/verilator_includer'):
            path = self.repository / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Native fixture source only; not a compiler/model.\n')
        for args in (['init', '--quiet'], ['add', 'src', 'include', 'bin'], [
                '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit',
                '--quiet', '-m', 'Native fixture source'
        ]):
            subprocess.run(['git', *args], cwd=self.repository, check=True, capture_output=True)
        self.head = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                            cwd=self.repository,
                                            text=True).strip()
        (self.repository / 'include/generated.mk').write_text('GENERATED_FIXTURE=1\n')
        self.config = {}
        for profile in self.contract['profiles']:
            wanted = ((self.cache / profile['expected']['path']).read_bytes()
                      if profile['expected']['mode'] == 'original_gold_exact' else b'PASSED\n')
            if profile['id'] in acceptance.DIAGNOSTIC_IDS:
                wanted = b'FAILED -- explicit diagnostic-only expected-output control\nPASSED\n'
            self.config[profile['id']] = {'stdout_base64': base64.b64encode(wanted).decode()}
        self.config_path = self.root / 'config.json'
        self.compiler = self.root / 'compiler.py'
        self.compiler.write_text('''#!/usr/bin/env python3
import base64, json, os
from pathlib import Path
import sys
if sys.argv[1:] == ['--version']:
    print('Verilator native-fixture-' + os.environ['FIXTURE_HEAD'])
    sys.exit(0)
if '--no-skip-identical' not in sys.argv:
    sys.exit(96)
profile = Path(sys.argv[-2]).stem
item = json.loads(Path(os.environ['FIXTURE_CONFIG']).read_text())[profile]
print(item.get('compile_stdout', ''), end='')
code = item.get('compile_exit', 0)
if code:
    sys.exit(code)
folder = Path(sys.argv[sys.argv.index('--Mdir') + 1])
folder.mkdir(parents=True)
(folder / 'Vt.mk').write_text('# Real native fixture; no C++ model build.\\n')
model = '#!/usr/bin/env python3\\nimport base64,sys\\nsys.stdout.buffer.write(base64.b64decode(' + repr(item['stdout_base64']) + '))\\nsys.exit(' + str(item.get('run_exit', 0)) + ')\\n'
(folder / 'Vt').write_text(model)
(folder / 'Vt').chmod(0o755)
''')
        self.compiler.chmod(0o755)
        self.make = self.root / 'make.py'
        self.make.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
if sys.argv[1:] != ['-C','obj','-f','Vt.mk','-j1']:
    sys.exit(97)
item=json.loads(Path(os.environ['FIXTURE_CONFIG']).read_text())[Path.cwd().name]
print(item.get('build_stdout',''),end='')
sys.exit(item.get('build_exit',0))
''')
        self.make.chmod(0o755)
        self.environment = dict(os.environ,
                                FIXTURE_HEAD=self.head,
                                FIXTURE_CONFIG=str(self.config_path))
        self.output = self.root / 'out'

    def cli(self, action, *, expected=0, head=None, contract=None):
        self.config_path.write_text(json.dumps(self.config))
        argv = [
            sys.executable,
            str(Path(acceptance.__file__).resolve()), action, '--contract',
            str(contract or acceptance.CONTRACT), '--repository',
            str(self.repository), '--compiler',
            str(self.compiler), '--expected-head', head or self.head, '--upstream-root',
            str(self.cache), '--output',
            str(self.output), '--make',
            str(self.make)
        ]
        result = subprocess.run(argv,
                                env=self.environment,
                                text=True,
                                capture_output=True,
                                check=False,
                                timeout=30)
        RECEIPTS.append({
            'test': self.id(),
            'command': argv,
            'native_exit': result.returncode,
            'expected_exit': expected,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def result(self):
        return json.loads((self.output / 'result.json').read_text())

    def rewrite(self, result):
        acceptance.save(self.output / 'result.json', result)

    def real_output(self, data):
        folder = self.root / ('native-output-' + str(len(RECEIPTS)))
        command = [
            sys.executable, '-c',
            'import sys;sys.stdout.buffer.write(bytes.fromhex(' + repr(data.hex()) + '))'
        ]
        result = acceptance.stage(folder, 'run', command, 5, self.environment)
        RECEIPTS.append({
            'test':
            self.id(),
            'native_stage':
            result,
            'raw_stdout':
            Path(result['log']).read_text(encoding='utf-8', errors='replace')
        })
        self.assertTrue(acceptance.stage_ok(result))
        return result['log']

    def test_complete18_and_separate16_gate(self):
        self.cli('run')
        result = self.result()
        self.assertEqual(result['counts'], {'passed': 16, 'expected_output_failed': 2})
        self.assertEqual(result['strict_gate_exit'], 0)
        self.assertEqual(result['full18_gate_exit'], 1)
        self.assertEqual(result['native_counts']['compile_exit_0'], 18)
        self.assertEqual(result['native_counts']['build_exit_0'], 18)
        self.assertEqual(result['native_counts']['run_exit_0'], 18)
        self.assertEqual(result['unrun_selected'], 0)
        self.assertEqual(result['reference_stages_executed'], 0)
        self.cli('check')

    def test_nonzero_native_despite_green_stdout(self):
        for code, text in [(7, 'PASSED\n'), (0, '%Error: injected error\n[0] %Fatal: injected\n')]:
            self.output = self.root / ('out-native-' + str(code))
            self.config['unary_minus'].update(compile_exit=code, compile_stdout=text)
            self.cli('run', expected=1)
            result = self.result()
            row = next(row for row in result['results'] if row['id'] == 'unary_minus')
            self.assertEqual(row['compile']['native_exit'], code)
            self.assertIsNone(row['build'])
            self.assertIsNone(row['run'])
            self.assertEqual(len(result['results']), 18)
            self.assertEqual(result['applicable_failed'], 1)
        # Exercise the build's actual final block in a real Bash process. The
        # fake native CLI preserves independent check/evidence after run fails.
        source = (acceptance.SOURCE_ROOT / 'ci/portable/build.bash').read_text()
        block = source[source.index('icarus_head=$(git rev-parse HEAD)\n'):]
        fake_bin = self.root / 'fake-python-bin'
        fake_bin.mkdir()
        python = fake_bin / 'python3'
        python.write_text('#!' + sys.executable + '\n' + '''import os,sys
action = sys.argv[2]
if sys.argv[1] == 'ci/portable/log_evidence.py':
    print('EVIDENCE_CALLED')
    sys.exit(0)
print(action.upper() + '_CALLED')
sys.exit(int(os.environ[action.upper() + '_FIXTURE_STATUS']))
''')
        python.chmod(0o755)
        shell = os.environ.get('BASH_BIN') or shutil.which('bash')
        for run_exit, check_exit in [(0, 0), (7, 0), (0, 9), (7, 9)]:
            environment = dict(self.environment,
                               PATH=str(fake_bin) + os.pathsep + os.environ['PATH'],
                               RUN_FIXTURE_STATUS=str(run_exit),
                               CHECK_FIXTURE_STATUS=str(check_exit))
            command = [shell, '-c', 'set -euo pipefail\n' + block]
            result = subprocess.run(command,
                                    cwd=self.repository,
                                    env=environment,
                                    capture_output=True,
                                    text=True,
                                    check=False)
            expected = 0 if (run_exit, check_exit) == (0, 0) else 1
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            self.assertIn('RUN_CALLED', result.stdout)
            self.assertIn('CHECK_CALLED', result.stdout)
            self.assertIn('EVIDENCE_CALLED', result.stdout)
            RECEIPTS.append({
                'test': self.id(),
                'command': command,
                'native_exit': result.returncode,
                'expected_exit': expected,
                'run_exit': run_exit,
                'check_exit': check_exit,
                'stdout': result.stdout,
                'stderr': result.stderr
            })

    def test_failed_duplicate_missing_and_embedded_pass_records(self):
        profile = self.contract['profiles'][0]
        for data in (b'FAILED\nPASSED\n', b'PASSED\nPASSED\n', b'', b'prefixPASSED\n'):
            with self.subTest(output=data):
                log = self.real_output(data)
                self.assertFalse(acceptance.output_check(log, profile, self.cache)['passed'])

    def test_original_gold_and_finish_notice_are_unfiltered(self):
        profile = next(p for p in self.contract['profiles'] if p['id'] == 'shift1')
        golden = (self.cache / profile['expected']['path']).read_bytes()
        self.assertTrue(
            acceptance.output_check(self.real_output(golden), profile, self.cache)['passed'])
        self.assertTrue(
            acceptance.output_check(self.real_output(golden.replace(b'\n', b'\r\n')), profile,
                                    self.cache)['passed'])
        for data in (golden + b'- source.v:1: Verilog $finish\n', b'CHANGED\n' + golden):
            self.assertFalse(
                acceptance.output_check(self.real_output(data), profile, self.cache)['passed'])

    def test_parent_zero_timeout_kills_descendant_group(self):
        command = [
            sys.executable, '-c',
            ('import subprocess,sys;child=subprocess.Popen([sys.executable,"-c",'
             '"import time;time.sleep(60)"]);print(child.pid,flush=True)')
        ]
        record = acceptance.stage(self.root / 'timeout', 'run', command, 0.3, self.environment)
        child_pid = int(Path(record['log']).read_text(encoding='utf-8').strip())
        self.assertEqual(record['native_exit'], 0)
        self.assertIs(record['timed_out'], True)
        self.assertFalse(acceptance.stage_ok(record))
        deadline = time.monotonic() + 3
        child_state = 'running'
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
                state = subprocess.run(
                    ['ps', '-o', 'stat=', '-p', str(child_pid)],
                    capture_output=True,
                    text=True,
                    check=False).stdout.strip()
                if state.startswith('Z') or not state:
                    child_state = 'reaped-or-zombie; no executing descendant'
                    break
            except ProcessLookupError:
                child_state = 'reaped'
                break
            time.sleep(0.02)
        if child_state == 'running':
            os.kill(child_pid, signal.SIGKILL)
        self.assertNotEqual(child_state, 'running')
        RECEIPTS.append({
            'test': self.id(),
            'native_stage': record,
            'descendant_pid': child_pid,
            'descendant_after_timeout': child_state
        })

    def test_boolean_exit_and_timeout_zero_receipts_reject(self):
        self.cli('run')
        original = self.result()
        for field, value in [('native_exit', False), ('timed_out', True)]:
            result = copy.deepcopy(original)
            step = result['results'][0]['compile']
            previous = json.loads(
                Path(step['log']).with_name('compile.finished.json').read_text(encoding='utf-8'))
            step[field] = value
            acceptance.save(Path(step['log']).with_name('compile.finished.json'), step)
            self.rewrite(result)
            self.cli('check', expected=1)
            acceptance.save(Path(step['log']).with_name('compile.finished.json'), previous)

    def test_missing_duplicate_counts_and_collection_reject(self):
        self.cli('run')
        original = self.result()
        variants = []
        for value in (original['results'][:-1], original['results'] + [original['results'][0]],
                      [original['results'][0], *original['results'][2:], original['results'][0]]):
            variants.append(dict(original, results=value))
        variants.extend([
            dict(original, selected=17),
            dict(original, skipped_selected=False),
            dict(original, skipped_selected=1),
            dict(original, collection_complete=False),
            dict(original, counts={'passed': 18})
        ])
        for result in variants:
            self.rewrite(result)
            self.cli('check', expected=1)

    def test_source_golden_license_hashes_reject(self):
        for name in ('ivtest/ivltests/addwide.v', 'ivtest/gold/shift1.gold', 'COPYING'):
            path = self.cache / name
            old = path.read_bytes()
            path.write_bytes(old + b'CHANGED\n')
            self.cli('run', expected=1)
            self.assertFalse(self.output.exists())
            path.write_bytes(old)

    def test_head_compiler_source_runtime_provenance_reject(self):
        self.cli('run')
        self.cli('check', head='0' * 40, expected=1)
        for path in (self.compiler, self.repository / 'src/provenance.txt',
                     self.repository / 'include/generated.mk',
                     self.repository / 'bin/verilator_includer'):
            old = path.read_bytes()
            path.write_bytes(old + b'\n#CHANGED\n')
            self.cli('check', expected=1)
            path.write_bytes(old)

    def test_diagnostic_native_crash_is_never_waived(self):
        self.config['sv_packed_port1'].update(build_exit=9, build_stdout='PASSED\n')
        self.cli('run', expected=1)
        result = self.result()
        self.assertEqual(result['applicable_counts'], {'passed': 16})
        self.assertEqual(result['diagnostic_infrastructure_failures'], ['sv_packed_port1'])
        self.assertEqual(result['strict_gate_exit'], 1)
        self.output = self.root / 'out-diagnostic-error0'
        self.config['sv_packed_port1'].pop('build_exit')
        self.config['sv_packed_port1']['stdout_base64'] = base64.b64encode(
            b'%Fatal: injected\nPASSED\n').decode()
        self.cli('run', expected=1)
        result = self.result()
        self.assertEqual(result['diagnostic_infrastructure_failures'], ['sv_packed_port1'])

    def test_mixed_primary_errors_preserve_ice_and_fatal(self):
        text = ('%Error-UNSUPPORTED: unsupported control\n%Error: Internal Error: injected\n'
                '[0] %Fatal: injected fatal\n%Error: Exiting due to 2 error(s)\n')
        self.config['nb_ec_concat'].update(compile_exit=1, compile_stdout=text)
        self.cli('run', expected=1)
        row = next(row for row in self.result()['results'] if row['id'] == 'nb_ec_concat')
        self.assertEqual(row['status'], 'compile_failed')
        self.assertEqual(row['compile']['error_headers'], text.splitlines())

    def test_logs_receipts_argv_headers_and_inventory_reject(self):
        self.cli('run')
        original = self.result()
        path = Path(original['results'][0]['run']['log'])
        data = path.read_bytes()
        path.write_bytes(data + b'PASSED\n')
        self.cli('check', expected=1)
        path.write_bytes(data)
        for field, value in [('command', ['wrong']), ('error_headers', ['%Error: false header'])]:
            result = copy.deepcopy(original)
            result['results'][0]['compile'][field] = value
            self.rewrite(result)
            self.cli('check', expected=1)
        self.rewrite(original)
        before = self.output / 'protected-before.json'
        after = self.output / 'protected-after.json'
        hashes = json.loads(before.read_text())
        hashes.pop(str(self.output / 'quiet_finish.cpp'))
        acceptance.save(before, hashes)
        acceptance.save(after, hashes)
        self.cli('check', expected=1)

    def test_pin_selection_contract_and_tls_reject(self):
        path = self.root / 'contract.json'
        variants = [
            dict(self.contract, source_commit='0' * 40),
            dict(self.contract, profiles=self.contract['profiles'][:-1]),
            dict(self.contract, applicable=self.contract['applicable'][:-1]),
            dict(self.contract, diagnostic_only=['nb_ec_concat'])
        ]
        for contract in variants:
            acceptance.save(path, contract)
            self.cli('run', contract=path, expected=1)
        for url in ('http://raw.githubusercontent.com/unsafe', 'https://example.invalid/unsafe'):
            with self.assertRaises(ValueError):
                acceptance.HTTPSRedirect().redirect_request(None, None, 302, '', {}, url)


def main():
    """Persist actual native control receipts alongside the 13-method summary."""
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AcceptanceTest)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    output = Path(
        os.environ.get('ICARUS_FIXTURE_RECEIPT',
                       acceptance.SOURCE_ROOT / 'out/icarus-fixtures.json'))
    output.parent.mkdir(parents=True, exist_ok=True)
    acceptance.save(
        output, {
            'test_methods':
            result.testsRun,
            'successful':
            result.wasSuccessful(),
            'native_controls':
            RECEIPTS,
            'scope': ('Real native exits/pipe/CLI failure controls; '
                      'fake model programs are not official SV simulations.')
        })
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
