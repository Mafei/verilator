#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# pylint: disable=missing-function-docstring
"""Check the audit container boundary without Docker, packages or HDL execution."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / 'ci/portable/rocky_audit.bash'
IMAGE = ('rockylinux/rockylinux:8.10@sha256:'
         'f5529992e67440c1a4ae7788244d4381c6909159a88eacd95b7523ae47ced82e')
HEAD = 'a' * 40

# Execute the real container shell through command doubles. Only Docker's mount
# and environment effects are emulated; dnf/setpriv/Python never affect the host.
COMMAND_DOUBLE = r'''import json,os,pathlib,subprocess,sys
name=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
def record(**fields):
    with open(os.environ['FAKE_LOG'],'a',encoding='utf-8') as stream:
        stream.write(json.dumps(dict(command=name,args=args,**fields))+'\n')
if name=='docker':
    script=sys.stdin.read()
    record(script=script)
    if os.environ.get('FAKE_DOCKER_STATUS'):
        sys.exit(int(os.environ['FAKE_DOCKER_STATUS']))
    env=os.environ.copy()
    mounts={}
    index=1
    while args[index].startswith('-'):
        flag=args[index]
        index+=1
        if flag in ('-e','-v','-w'):
            value=args[index]
            index+=1
            if flag=='-e':
                key,value=value.split('=',1)
                env[key]=value
            elif flag=='-v':
                source,destination=value.rsplit(':',1)
                mounts[destination]=source
            else:
                assert value=='/work'
        else:
            assert flag in ('--rm','-i')
    if env.get('GITHUB_OUTPUT') in mounts:
        env['GITHUB_OUTPUT']=mounts[env['GITHUB_OUTPUT']]
    result=subprocess.run(args[index+1:],input=script,text=True,env=env,
                          cwd=mounts['/work'],check=False)
    sys.exit(result.returncode)
if name=='setpriv':
    record()
    assert args[:5]==['--reuid',str(os.getuid()),'--regid',str(os.getgid()),'--clear-groups']
    os.execvpe(args[5],args[5:],os.environ)
if name=='mktemp':
    record()
    assert args==['-d','/tmp/verilator-owner-home.XXXXXX']
    home=pathlib.Path(os.environ['FAKE_ROOT'])/'owner-home'
    home.mkdir(exist_ok=True)
    print(home)
elif name=='dnf':
    record()
elif name=='git':
    record()
    assert args==['rev-parse','HEAD']
    print('a'*40)
elif name=='python3.11':
    record(home=os.environ['HOME'],run_id=os.environ.get('GITHUB_RUN_ID'),
           attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
           prior=os.environ.get('PRODUCER_PRIOR_RESULT'))
    if args[0]=='ci/portable/review_artifacts.py':
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
            stream.write('core_review=original-child-output\n')
    sys.exit(int(os.environ.get('FAKE_AUDIT_STATUS','0')))
else:
    raise AssertionError(name)
'''


class RockyAuditTest(unittest.TestCase):
    """Keep the original path/owner and propagate the audit's actual status."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
            prefix='rocky audit ')
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.bin = self.folder / 'bin'
        self.bin.mkdir()
        for name in ('docker', 'dnf', 'setpriv', 'mktemp', 'git', 'python3.11'):
            path = self.bin / name
            path.write_text('#!' + sys.executable + '\n' + COMMAND_DOUBLE, encoding='utf-8')
            path.chmod(0o700)
        self.log = self.folder / 'commands.jsonl'
        self.output = self.folder / 'step output'
        self.output.write_text('existing=preserved\n', encoding='utf-8')
        self.env = dict(os.environ,
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        FAKE_LOG=str(self.log),
                        FAKE_ROOT=str(self.folder),
                        GITHUB_OUTPUT=str(self.output),
                        GITHUB_RUN_ID='123',
                        GITHUB_RUN_ATTEMPT='2',
                        PRODUCER_PRIOR_RESULT='failure')

    def invoke(self, *args, status=0):
        self.env['FAKE_AUDIT_STATUS'] = str(status)
        return subprocess.run(['bash', str(WRAPPER), *args],
                              env=self.env,
                              capture_output=True,
                              text=True,
                              check=False,
                              timeout=10)

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def assert_container(self, commands, mounts):
        docker = next(row for row in commands if row['command'] == 'docker')
        args = docker['args']
        self.assertEqual(args[0], 'run')
        self.assertEqual(args.count(IMAGE), 1)
        self.assertEqual(args[args.index(IMAGE) + 1:][:3], ['bash', '-s', '--'])
        self.assertEqual([args[i + 1] for i, word in enumerate(args) if word == '-v'], mounts)
        self.assertEqual(args[args.index('-w') + 1], '/work')
        self.assertIn('ARTIFACT_UID=' + str(os.getuid()), args)
        self.assertIn('ARTIFACT_GID=' + str(os.getgid()), args)
        self.assertNotIn('--privileged', args)
        installs = [row['args'] for row in commands if row['command'] == 'dnf']
        self.assertEqual(installs, [['-y', 'install', 'python3.11', 'git', 'util-linux']])
        python = [row for row in commands if row['command'] == 'python3.11']
        self.assertEqual(len(python), 1)
        self.assertEqual(python[0]['home'], str(self.folder / 'owner-home'))
        return docker, python[0]

    def test_shell_syntax(self):
        result = subprocess.run(['bash', '-n', str(WRAPPER)], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_workflow_keeps_fatal_audits_in_the_producer_context(self):
        source = (ROOT / '.github/workflows/portable-fourstate.yml').read_text()
        macos, rocky = source.split('\n  macos:\n', 1)[1].split('\n  rocky8:\n', 1)

        def step(job, name):
            return next(block for block in job.split('      - name: ')
                        if block.startswith(name + '\n'))

        for job, mode_prefix in ((rocky, 'bash ci/portable/rocky_audit.bash'),
                                 (macos, 'python3 ci/portable')):
            verify = step(job, 'Independently verify recorded results')
            producer = step(job, 'Check local producer files before upload without running models')
            self.assertIn('        id: producer_review\n', producer)
            self.assertIn('          PRODUCER_PRIOR_RESULT: ${{ job.status }}\n', producer)
            self.assertNotIn('continue-on-error:', verify + producer)
            if job == rocky:
                self.assertIn('        run: ' + mode_prefix + ' regressions\n', verify)
                self.assertIn('        run: ' + mode_prefix + ' producer\n', producer)
            else:
                self.assertIn('        run: ' + mode_prefix + '/check_results.py\n', verify)
                self.assertIn(mode_prefix + '/review_artifacts.py producer', producer)
                self.assertIn('--platform macos-arm64 --producer-root "$(pwd -P)"', producer)

    def test_regression_audit_uses_original_mount_and_owner(self):
        result = self.invoke('regressions')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        docker, python = self.assert_container(self.commands(), [str(ROOT) + ':/work'])
        self.assertEqual(docker['args'][-1], 'regressions')
        self.assertEqual(python['args'], ['ci/portable/check_results.py'])
        self.assertNotIn('GITHUB_OUTPUT=/tmp/github-output', docker['args'])
        self.assertEqual(self.output.read_text(), 'existing=preserved\n')

    def test_producer_output_is_bound_to_current_step_and_keeps_context(self):
        result = self.invoke('producer')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        docker, python = self.assert_container(
            self.commands(),
            [str(ROOT) + ':/work', str(self.output) + ':/tmp/github-output'])
        self.assertEqual(docker['args'][-1], 'producer')
        self.assertIn('GITHUB_OUTPUT=/tmp/github-output', docker['args'])
        self.assertEqual(python['args'], [
            'ci/portable/review_artifacts.py', 'producer', '--expected-head', HEAD, '--run-id',
            '123', '--platform', 'rocky8-x86_64', '--producer-root', '/work', '--prior-result',
            'failure', '--output', 'out/producer-core-review.json'
        ])
        self.assertEqual((python['run_id'], python['attempt'], python['prior']),
                         ('123', '2', 'failure'))
        self.assertEqual(self.output.read_text(),
                         'existing=preserved\ncore_review=original-child-output\n')

    def test_nonzero_audit_status_is_not_hidden(self):
        for mode in ('regressions', 'producer'):
            for status in (1, 2, 10, 126, 127):
                with self.subTest(mode=mode, status=status):
                    before = self.output.read_text()
                    result = self.invoke(mode, status=status)
                    self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                    expected = before + ('core_review=original-child-output\n'
                                         if mode == 'producer' else '')
                    self.assertEqual(self.output.read_text(), expected)

    def test_docker_start_failure_is_not_hidden(self):
        self.env['FAKE_DOCKER_STATUS'] = '125'
        result = self.invoke('regressions')
        self.assertEqual(result.returncode, 125, result.stdout + result.stderr)
        self.assertEqual([row['command'] for row in self.commands()], ['docker'])

    def test_invalid_mode_never_invokes_docker(self):
        for args in ((), ('unknown', ), ('producer', 'extra')):
            with self.subTest(args=args):
                result = self.invoke(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(self.log.exists())

    def test_missing_or_invalid_producer_context_never_invokes_docker(self):
        original = self.env.copy()
        symlink = self.folder / 'output-link'
        symlink.symlink_to(self.output)
        for key, value in (('GITHUB_OUTPUT', ''), ('GITHUB_OUTPUT', 'relative-output'),
                           ('GITHUB_OUTPUT', str(self.folder / 'missing')),
                           ('GITHUB_OUTPUT', str(self.folder)), ('GITHUB_OUTPUT', str(symlink)),
                           ('GITHUB_RUN_ID', ''), ('GITHUB_RUN_ID', '123\n'),
                           ('GITHUB_RUN_ATTEMPT', '0'), ('PRODUCER_PRIOR_RESULT', 'cancelled')):
            with self.subTest(key=key, value=value):
                self.env = dict(original, **{key: value})
                result = self.invoke('producer')
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(self.log.exists())


if __name__ == '__main__':
    unittest.main()
