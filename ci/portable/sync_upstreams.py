#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
r"""Audit fixed upstreams and optionally merge into a new, isolated candidate.

Examples (use a full clone and a clean worktree):
  python3 ci/portable/sync_upstreams.py --base fourstate-portable
  python3 ci/portable/sync_upstreams.py --base fourstate-portable \
      --candidate upstream-candidate --worktree /tmp/verilator-candidate \
      --report /tmp/verilator-upstream-report.json

Audit mode fetches objects and updates refs/portable-upstreams/* observation
refs, but never changes a source branch or worktree. These refs detect upstream
rewinds on later runs. The JSON report is always printed, with optional atomic
file output outside either worktree. Candidates are never pushed, published,
or merged back. A conflicted candidate is left in place for inspection.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid


# Order is intentional: Veripool mainline, then both tracked Antmicro variants.
# There is no CLI override for repository URLs or branch names.
UPSTREAMS = (
    ('veripool-master', 'https://github.com/verilator/verilator.git', 'master'),
    ('antmicro-fourstate', 'https://github.com/antmicro/verilator.git', 'dev/fourstate'),
    ('antmicro-4-state-logic', 'https://github.com/antmicro/verilator.git', 'feature/4_state_logic'),
)


class SyncError(Exception):
    """A safe diagnostic that contains no local absolute paths or Git output."""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def git(repo, *arguments, check=True, input_text=None):
    environment = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_MERGE_AUTOEDIT='no', LC_ALL='C')
    result = subprocess.run(['git', '-C', str(repo), *arguments], input=input_text,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding='utf-8', errors='replace', env=environment)
    if check and result.returncode:
        operation = next((arg for index, arg in enumerate(arguments)
                          if not arg.startswith('-') and (index == 0 or arguments[index - 1] != '-c')),
                         'operation')
        raise SyncError('Git {} failed (exit {}); inspect Git locally'.format(operation, result.returncode))
    return result


def resolve_commit(repo, revision):
    return git(repo, 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}').stdout.strip()


def ancestor(repo, older, newer):
    result = git(repo, 'merge-base', '--is-ancestor', older, newer, check=False)
    if result.returncode not in (0, 1):
        raise SyncError('Git ancestry check failed')
    return result.returncode == 0


def read_ref(repo, ref):
    result = git(repo, 'rev-parse', '--verify', '--quiet', '--end-of-options', ref, check=False)
    if result.returncode not in (0, 1):
        raise SyncError('Git reference check failed')
    return result.stdout.strip() if result.returncode == 0 else None


def paths(output):
    return sorted(set(filter(None, output.split('\0'))))


def dirty_paths(repo):
    return sorted(set(paths(git(repo, 'diff', '--name-only', '-z').stdout)
                      + paths(git(repo, 'diff', '--cached', '--name-only', '-z').stdout)
                      + paths(git(repo, 'ls-files', '--others', '--exclude-standard', '-z').stdout)))


def within(path, directory):
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def audit_commit(repo, base, tip):
    merge_base = git(repo, 'merge-base', '--all', base, tip, check=False)
    if merge_base.returncode not in (0, 1):
        raise SyncError('Git merge-base check failed')
    bases = merge_base.stdout.split()
    counts = git(repo, 'rev-list', '--left-right', '--count', base + '...' + tip).stdout.split()
    if base == tip:
        relation = 'identical'
    elif ancestor(repo, tip, base):
        relation = 'upstream_contained'
    elif ancestor(repo, base, tip):
        relation = 'base_ancestor'
    else:
        relation = 'diverged' if bases else 'unrelated'
    return {
        'relation': relation,
        'merge_bases': bases,
        'base_only_commits': int(counts[0]),
        'upstream_only_commits': int(counts[1]),
        'changed_files': paths(git(repo, 'diff', '--name-only', '-z', base, tip).stdout),
    }


def prepare(args, report):
    repo = Path(args.repo).resolve()
    repo = Path(git(repo, 'rev-parse', '--show-toplevel').stdout.strip()).resolve()
    if git(repo, 'rev-parse', '--is-shallow-repository').stdout.strip() == 'true':
        raise SyncError('A full clone is required for ancestry and rewind checks')
    report['original_head'] = resolve_commit(repo, 'HEAD')
    report['base_commit'] = resolve_commit(repo, args.base)
    worktree = Path(args.worktree).resolve() if args.worktree else None
    report_file = Path(args.report).resolve() if args.report else None
    if report_file and (within(report_file, repo) or (worktree and within(report_file, worktree))):
        raise SyncError('The report file must be outside the source and candidate worktrees')
    if report_file and not report_file.parent.is_dir():
        raise SyncError('The report directory must already exist')
    args.report_validated = True
    dirty = dirty_paths(repo)
    if dirty:
        report['dirty_files'] = dirty
        raise SyncError('The source worktree is dirty')
    if args.candidate:
        if args.candidate.startswith('-') or git(repo, 'check-ref-format', '--branch', args.candidate,
                                               check=False).returncode:
            raise SyncError('The candidate branch name is invalid')
        if read_ref(repo, 'refs/heads/' + args.candidate):
            raise SyncError('The candidate branch already exists')
        if within(worktree, repo) or worktree.exists() or Path(args.worktree).is_symlink():
            raise SyncError('The candidate worktree must be a new path outside the source worktree')

    temporary_refs = []
    transaction = ['start']
    try:
        fetch_namespace = 'refs/portable-sync/incoming/' + uuid.uuid4().hex
        for name, url, branch in UPSTREAMS:
            observation_ref = 'refs/portable-upstreams/' + name
            previous = read_ref(repo, observation_ref)
            temporary_ref = fetch_namespace + '/' + name
            temporary_refs.append(temporary_ref)
            git(repo, 'fetch', '--no-tags', '--no-write-fetch-head', '--no-recurse-submodules',
                url, 'refs/heads/' + branch + ':' + temporary_ref)
            tip = resolve_commit(repo, temporary_ref)
            entry = {
                'name': name, 'repository': url, 'branch': branch, 'commit': tip,
                'fetched_at_utc': utc_now(), 'previous_observed_commit': previous,
                'commit_date': git(repo, 'show', '-s', '--format=%cI', tip).stdout.strip(),
                'rewound_or_replaced': bool(previous and not ancestor(repo, previous, tip)),
            }
            entry.update(audit_commit(repo, report['base_commit'], tip))
            report['upstreams'].append(entry)
            transaction.append('update {} {} {}'.format(observation_ref, tip, previous or '0' * len(tip)))
        if any(entry['rewound_or_replaced'] for entry in report['upstreams']):
            raise SyncError('An upstream ref was rewound or replaced; observation refs were not advanced')
        if any(entry['relation'] == 'unrelated' for entry in report['upstreams']):
            raise SyncError('An upstream has unrelated history; automatic merging is refused')
        if resolve_commit(repo, 'HEAD') != report['original_head'] or dirty_paths(repo):
            raise SyncError('The source worktree changed during the audit; retry from a clean worktree')
        transaction.extend(['prepare', 'commit'])
        git(repo, 'update-ref', '--stdin', input_text='\n'.join(transaction) + '\n')
        report['observation_refs_updated'] = True
    finally:
        for temporary_ref in temporary_refs:
            if git(repo, 'update-ref', '-d', temporary_ref, check=False).returncode:
                report.setdefault('warnings', []).append('Temporary observation ref cleanup failed')

    report['updates_available'] = any(entry['upstream_only_commits'] for entry in report['upstreams'])
    if not args.candidate:
        report['status'] = 'audit_complete'
        return 0
    if not report['updates_available']:
        report['status'] = 'up_to_date'
        return 0

    # Fail before worktree creation if local commit identity is unavailable.
    git(repo, 'var', 'GIT_AUTHOR_IDENT')
    git(repo, 'var', 'GIT_COMMITTER_IDENT')
    if read_ref(repo, 'refs/heads/' + args.candidate) or worktree.exists() or Path(args.worktree).is_symlink():
        raise SyncError('The candidate branch or worktree appeared during the audit; retry with a new name')
    git(repo, '-c', 'core.hooksPath=' + os.devnull, 'worktree', 'add', '-b', args.candidate,
        str(worktree), report['base_commit'])
    report['candidate'] = {'branch': args.candidate, 'merges': [], 'head': report['base_commit']}
    for entry in report['upstreams']:
        before = resolve_commit(worktree, 'HEAD')
        step = {'upstream': entry['name'], 'commit': entry['commit'], 'previous_head': before}
        report['candidate']['merges'].append(step)
        if ancestor(worktree, entry['commit'], before):
            step['status'] = 'already_contained'
            continue
        result = git(worktree, '-c', 'core.hooksPath=' + os.devnull, '-c', 'commit.gpgsign=false',
                     '-c', 'merge.autoStash=false', '-c', 'rerere.enabled=false',
                     'merge', '--no-ff', '--no-edit', '--no-stat', entry['commit'], check=False)
        report['candidate']['head'] = resolve_commit(worktree, 'HEAD')
        if result.returncode:
            conflicts = paths(git(worktree, 'diff', '--name-only', '--diff-filter=U', '-z').stdout)
            step.update(status='conflict' if conflicts else 'merge_failed', unmerged_files=conflicts,
                        exit_code=result.returncode)
            report['status'] = step['status']
            report['error'] = 'Candidate merge stopped; inspect the isolated worktree'
            return 1
        step.update(status='merged', head=report['candidate']['head'])
    report['status'] = 'candidate_ready'
    return 0


def parser():
    result = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    result.add_argument('--base', required=True, help='Explicit base commit or ref; never inferred from HEAD')
    result.add_argument('--repo', default='.', help='Full Git clone to audit (default: current directory)')
    result.add_argument('--candidate', help='New branch to create; omitted means audit only')
    result.add_argument('--worktree', help='New independent worktree path; required with --candidate')
    result.add_argument('--report', help='Optional JSON file outside both worktrees; JSON is also printed')
    return result


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    args.report_validated = False
    if bool(args.candidate) != bool(args.worktree):
        argument_parser.error('--candidate and --worktree must be provided together')
    report = {
        'schema_version': 1, 'started_at_utc': utc_now(), 'mode': 'candidate' if args.candidate else 'audit',
        'status': 'blocked', 'upstreams': [], 'observation_refs_updated': False,
    }
    try:
        exit_code = prepare(args, report)
    except (SyncError, OSError) as error:
        report['error'] = str(error) if isinstance(error, SyncError) else 'Local filesystem operation failed'
        exit_code = 2
    report['finished_at_utc'] = utc_now()
    encoded = json.dumps(report, indent=2, sort_keys=True) + '\n'
    # Do not write a report rejected during path validation.
    if args.report and args.report_validated:
        temporary_path = None
        try:
            destination = Path(args.report).resolve()
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                             prefix='.upstream-sync-', delete=False) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(encoded)
            os.replace(temporary_path, destination)
        except OSError:
            if temporary_path:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    report.setdefault('warnings', []).append('Temporary report cleanup failed')
            report['status'] = 'report_write_failed'
            report['error'] = 'Writing the report file failed; use the JSON printed here'
            exit_code = 2
            encoded = json.dumps(report, indent=2, sort_keys=True) + '\n'
    sys.stdout.write(encoded)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
