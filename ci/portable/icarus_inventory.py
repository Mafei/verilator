#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Inventory the pinned original Icarus default parsers without running models.

The observation hook must preserve the original parser state. Python captures
the original process_test options with execution functions replaced by stubs.
This inventory adds no compiler or simulation pass credit.
"""

import argparse
import collections
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

PIN = "f45ffabed3212a106f01cb362ef42c5d293f4513"
PERL_FIELDS = [
    "srcpath", "testtype", "args", "plargs", "diff", "gold", "unordered", "testmod", "offset"
]
STANDARD = [("regress-ivl1.list", ""), ("regress-vlg.list", ""), ("regress-sv.list", ""),
            ("regress-vhdl.list", ""), ("regress-synth.list", "-S")]
PRIOR_SELECTION_SHA = "ce063b8824b930198819261c44265c5b6e6cc2d865b9221b736c511e685c7827"
PRIOR_CORE_SHA = "d90ada099b8aff78e164a2a70889b170200859cd6d8b90d084497dbb6f21d347"


def digest(path):
    """Bind file bytes and their size."""
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def file_record(ivtest, relative):
    """Keep missing optional gold files explicit rather than inventing content."""
    path = ivtest / relative
    if not path.is_file():
        return {"path": "ivtest/" + str(relative), "exists": False}
    raw = path.read_bytes()
    return {
        "path":
        "ivtest/" + str(relative),
        "exists":
        True,
        **digest(path), "git_blob_sha1":
        hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    }


def logical_rows(path):
    """Record physical locations; original parsers make all acceptance decisions."""
    physical = path.read_text().splitlines()
    result = []
    index = 0
    while index < len(physical):
        start = index + 1
        line = physical[index]
        while line.endswith("\\") and index + 1 < len(physical):
            index += 1
            line = line[:-1] + physical[index].lstrip()
        clean = line.split("#", 1)[0].strip()
        if clean:
            result.append({
                "physical_line_start": start,
                "physical_line_end": index + 1,
                "logical_text": clean,
                "fields": clean.split()
            })
        index += 1
    return result


def perl_parse(ivtest, trace=False):
    """Read the original RegressionList module, with an optional passive trace."""
    program = r'''
use JSON::PP;
my $trace = shift @ARGV;
open(my $fh, '<', 'perl-lib/RegressionList.pm') or die $!;
my $source = do { local $/; <$fh> }; close($fh);
if ($trace) {
  my $needle = 'push (@testlist, $tname);';
  my $replacement = $needle . q{ push @::trace_rows, {name=>$tname, path=>$regress_fn, line_end=>0+$., slot=>scalar(@testlist)-1};};
  my $count = ($source =~ s/\Q$needle\E/$replacement/g);
  die "Unexpected observation count $count" unless $count == 1;
}
eval $source; die $@ if $@;
for my $f (@ARGV) {
  my ($path,$opt) = split(/:/,$f,2);
  RegressionList::read_regression_list($path,14,0,defined($opt)?$opt:'');
}
no strict 'refs';
my %state; $state{testlist} = \@RegressionList::testlist;
for my $field (qw(srcpath testtype args plargs diff gold unordered testmod offset)) {
  $state{$field} = \%{"RegressionList::$field"};
}
print JSON::PP->new->canonical->encode({state=>\%state,trace=>\@::trace_rows});
'''
    output = subprocess.check_output(
        ["perl", "-e", program,
         str(int(trace)), *[p + ":" + o for p, o in STANDARD]],
        cwd=ivtest,
        text=True)
    return json.loads(output)


def vpi_parse(ivtest, trace=False):
    """Evaluate only the original Linux/default VPI list-reading subroutine."""
    program = r'''
use JSON::PP;
my $trace = shift @ARGV;
$with_pli1=0; $sys='other'; $ver=14; $regress_fn='vpi_regress.list';
open(my $fh, '<', 'vpi_reg.pl') or die $!;
my $source = do { local $/; <$fh> }; close($fh);
my $start=index($source,'sub read_regression_list {');
my $end=index($source,'sub execute_regression {');
die 'VPI parser bounds' unless $start>=0 && $end>$start;
$source=substr($source,$start,$end-$start);
if ($trace) {
  my $needle='push (@testlist,$tname);';
  my $replacement=$needle . q{ push @::trace_rows,{name=>$tname,path=>$regress_fn,line_end=>0+$.,slot=>scalar(@testlist)-1,type=>$testtype};};
  my $count=($source =~ s/\Q$needle\E/$replacement/g);
  die "Unexpected VPI observation count $count" unless $count==1;
}
eval $source; die $@ if $@; read_regression_list();
print JSON::PP->new->canonical->encode({state=>{testlist=>\@testlist,args=>\%args,ccode=>\%ccode,goldfile=>\%goldfile,cargs=>\%cargs},trace=>\@trace_rows});
'''
    return json.loads(
        subprocess.check_output(["perl", "-e", program, str(int(trace))], cwd=ivtest, text=True))


def classify(row):
    """Partition adapters, without equating an adapter gap to unsupported SV."""
    typ = row["effective_type"]
    blockers = []
    if typ == "NI":
        blockers.append("upstream_not_implemented_do_not_execute_or_pass")
    if typ in ("EF", "TE"):
        blockers.append("upstream_expected_failure_or_translation_contract_requires_review")
    if row["family"] == "vpi":
        blockers.append("vpi_requires_explicit_native_api_adapter_not_vvp_plugin_loading")
    if row.get("gold_mode") == "compiler_and_runtime_log":
        blockers.append("icarus_specific_combined_diagnostics_require_separate_semantic_oracle")
    if row.get("gold_mode") == "per_stage_logs":
        blockers.append("icarus_specific_per_stage_diagnostics_require_separate_semantic_oracle")
    if row.get("gold_mode") == "external_file_diff":
        blockers.append("external_file_comparison_requires_original_diff_contract")
    if typ in ("CO", "CN", "CE", "RE"):
        blockers.append("negative_or_compile_only_contract_not_runtime_pass")
    generations = {
        "-g1995", "-g2001", "-g2001-noconfig", "-g2005", "-g2005-sv", "-g2009", "-g2012", "-g2017",
        "-g2023"
    }
    for arg in row.get("iverilog_args", []):
        if arg not in generations and not arg.startswith("-D"):
            blockers.append("unmapped_icarus_argument:" + arg)
    if not row.get("source", {}).get("exists"):
        blockers.append("missing_primary_source")
    row["adapter_partition"] = ("portable_selfchecking_normal" if not blockers and typ == "normal"
                                else "needs_explicit_adapter_or_contract")
    row["static_adapter_reasons"] = sorted(set(blockers))
    row["initial_result_category"] = "UNRUN"
    row["source_features_are_static_hints_not_certification"] = True
    patterns = {
        "fourstate_net_and_operators":
        r"(tri|pull|strength|unknown|isunknown|xnor|xor|mux|shift|casez|casex|bufif|notif|supply)",
        "scheduling_nba_event":
        r"(nba|nb_|assign_nb|event|fork|join|wait|delay|always|clock|strobe|monitor)",
        "types_arrays_ports":
        r"(array|packed|struct|union|enum|cast|port|signed|select|partsel|bitsel|param|typedef)",
        "interface":
        r"(interface|modport|virtual)",
        "classes":
        r"(class|object|inherit|extends)",
        "randomization":
        r"(rand|constraint)",
        "assertion":
        r"(assert|property|sequence)",
        "coverage":
        r"(cover)",
        "behavioral_model_io":
        r"(readmem|writemem|fopen|fread|fwrite|fseek|sscanf|plusarg|timeunit|timescale|realtime)",
    }
    row["feature_hints"] = [
        name for name, pattern in patterns.items() if re.search(pattern, row["test_id"])
    ]


def python_options(driver, item):
    """Capture the original options object while native execution is disabled."""
    seen = []

    def trace(frame, event, _unused):
        if frame.f_code is driver.process_test.__code__ and event == "return":
            seen.append(copy.deepcopy(frame.f_locals["it_opts"]))
        return trace

    previous_trace = sys.gettrace()
    sys.settrace(trace)
    try:
        driver.process_test(item, {"strict": False, "force-sv": False, "vlog95": False})
    finally:
        sys.settrace(previous_trace)
    assert len(seen) == 1
    return seen[0]


def main():  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Rebuild deterministic default metadata and a result-independent selection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.repo = args.repo.resolve(strict=True)
    head = subprocess.check_output(["git", "-C", str(args.repo), "rev-parse", "HEAD"],
                                   text=True).strip()
    if head != PIN:
        raise SystemExit("Pinned Icarus checkout mismatch: " + head)
    args.out.mkdir(parents=True, exist_ok=False)
    ivtest = args.repo / "ivtest"
    raw_lists = {
        p.name: {
            "file": file_record(ivtest, p.name),
            "rows": logical_rows(p)
        }
        for p in sorted(ivtest.glob("*.list"))
    }
    scenarios = []
    comparisons = []

    def attach(row, profile, ordinal):
        row.update(profile=profile,
                   ordinal=ordinal,
                   scenario_id=f"{profile}:{ordinal:04d}:{row['test_id']}")
        classify(row)
        scenarios.append(row)

    original = perl_parse(ivtest)
    observed = perl_parse(ivtest, True)
    assert original["state"] == observed["state"], "Perl observation altered parser state"
    comparisons.append({"profile": "perl-default", "original_and_observed_equal": True})
    state = original["state"]
    locations = {row["slot"]: row for row in observed["trace"]}
    ordinal = 0
    for slot, name in enumerate(state["testlist"]):
        if not name:
            continue
        ordinal += 1
        loc = locations[slot]
        raw = next(row for row in raw_lists[loc["path"]]["rows"]
                   if row["physical_line_end"] == loc["line_end"])
        fields = {field: state[field].get(name) for field in PERL_FIELDS}
        gold_mode = ("external_file_diff" if fields["diff"] else
                     "compiler_and_runtime_log" if fields["gold"] else "selfchecking_passed_line")
        row = {
            "family": "perl-vvp",
            "test_id": name,
            "effective_type": fields["testtype"],
            "parser_fields": fields,
            "original_list": "ivtest/" + loc["path"],
            **raw, "iverilog_args_string": fields["args"] or "",
            "iverilog_args": shlex.split(fields["args"] or ""),
            "runtime_plusargs_string": fields["plargs"] or "",
            "top": fields["testmod"],
            "source": file_record(ivtest, f"{fields['srcpath']}/{name}.v"),
            "gold_mode": gold_mode,
            "gold": file_record(ivtest, fields["gold"]) if fields["gold"] else None,
            "oracle": "ivtest/perl-lib/Diff.pm",
            "original_parser_verified_equal": True
        }
        row["effective_oracle"] = (
            "none_not_executed" if fields["testtype"] == "NI" else
            "compile_success_only" if fields["testtype"] in ("CO", "CN") else
            "compile_error_only" if fields["testtype"] == "CE" and not fields["gold"]
            and not fields["diff"] else "runtime_error_only" if fields["testtype"] == "RE"
            and not fields["gold"] and not fields["diff"] else gold_mode)
        attach(row, "perl-default", ordinal)

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ivtest))
    test_lists = importlib.import_module("test_lists")
    driver = importlib.import_module("vvp_reg")
    for name in ("run_normal", "run_CE", "run_EF", "run_TE"):
        setattr(driver.run_ivl, name, lambda *_unused: [0, "INVENTORY_ONLY_NO_EXECUTION"])
    previous_cwd = Path.cwd()
    os.chdir(ivtest)
    try:
        items = test_lists.read_lists(["regress-vvp.list"])
        raw_by_key = {row["fields"][0]: row for row in raw_lists["regress-vvp.list"]["rows"]}
        for ordinal, item in enumerate(items, 1):
            options = python_options(driver, item)
            stages = ("iverilog", ) if options["type"] == "CE" else ("iverilog", "vvp")
            gold = ([
                file_record(ivtest, f"gold/{options['gold']}-{stage}-{stream}.gold")
                for stage in stages for stream in ("stdout", "stderr")
            ] if options["gold"] is not None else None)
            row = {
                "family": "python-vvp",
                "test_id": item[0],
                "effective_type": options["type"],
                "original_list": "ivtest/regress-vvp.list",
                **raw_by_key[item[0]], "json_config": file_record(ivtest, item[1]),
                "parser_fields": options,
                "iverilog_args": options["iverilog_args"],
                "source": file_record(ivtest, options["source"]),
                "gold_mode":
                "per_stage_logs" if options["gold"] is not None else "selfchecking_passed_line",
                "gold": gold,
                "oracle": "ivtest/run_ivl.py",
                "original_process_test_used_without_execution": True
            }
            row["effective_oracle"] = ("none_not_executed" if options["type"] == "NI" else
                                       "compile_error_only" if options["type"] == "CE"
                                       and options["gold"] is None else row["gold_mode"])
            attach(row, "python-default", ordinal)
    finally:
        os.chdir(previous_cwd)

    original = vpi_parse(ivtest)
    observed = vpi_parse(ivtest, True)
    assert original["state"] == observed["state"], "VPI observation altered parser state"
    comparisons.append({"profile": "vpi-linux-default", "original_and_observed_equal": True})
    state = original["state"]
    locations = {row["slot"]: row for row in observed["trace"]}
    ordinal = 0
    for slot, name in enumerate(state["testlist"]):
        if not name:
            continue
        ordinal += 1
        loc = locations[slot]
        raw = next(row for row in raw_lists["vpi_regress.list"]["rows"]
                   if row["physical_line_end"] == loc["line_end"])
        row = {
            "family": "vpi",
            "test_id": name,
            "effective_type": loc["type"],
            "original_list": "ivtest/vpi_regress.list",
            **raw, "source": file_record(ivtest, f"vpi/{name}.v"),
            "c_source": file_record(ivtest, "vpi/" + state["ccode"].get(name, "")),
            "gold_mode": "compiler_and_runtime_log",
            "gold": file_record(ivtest, "vpi_gold/" + state["goldfile"].get(name, "")),
            "iverilog_args": shlex.split(state["args"].get(name) or ""),
            "c_args_string": state["cargs"].get(name),
            "original_parser_verified_equal": True,
            "effective_oracle": "compiler_and_runtime_log"
        }
        attach(row, "vpi-linux-default", ordinal)

    inputs = []
    tree = subprocess.check_output(
        ["git", "-C", str(args.repo), "ls-tree", "-rz", "HEAD", "ivtest"]).split(b"\0")
    for raw in tree:
        if not raw:
            continue
        identity, relative = raw.split(b"\t", 1)
        mode, kind, blob = identity.decode().split()
        assert kind == "blob"
        path = args.repo / os.fsdecode(relative)
        data = path.read_bytes()
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == blob
        assert not path.is_symlink(), "Pinned fixture symlinks require explicit handling"
        inputs.append({
            "path": os.fsdecode(relative),
            **digest(path), "symlink": False,
            "git_blob_sha1": blob,
            "git_mode": mode
        })
    per = [row for row in scenarios if row["profile"] == "perl-default"]
    py = [row for row in scenarios if row["profile"] == "python-default"]
    eligible = [
        row for row in per + py if row["adapter_partition"] == "portable_selfchecking_normal"
    ]
    rule = ("Filter structurally to normal selfchecking source-existing cases with no static "
            "nontrivial-Icarus-argument adapter blocker, then floor(i*N/128), i=0..127. "
            "This structural filter does not mean support/pass. "
            "Preserve all excluded slots in full inventory as UNRUN.")
    selection = {
        "rule": rule,
        "eligible_denominator": len(eligible),
        "selected_denominator": 128,
        "scenario_ids": [eligible[(i * len(eligible)) // 128]["scenario_id"] for i in range(128)]
    }
    selection256 = {
        "rule": rule.replace("128", "256").replace("127", "255"),
        "eligible_denominator": len(eligible),
        "selected_denominator": 256,
        "includes_all_first128": True,
        "scenario_ids": [eligible[(i * len(eligible)) // 256]["scenario_id"] for i in range(256)]
    }
    assert set(selection["scenario_ids"]).issubset(selection256["scenario_ids"])
    summary = {
        "pin": PIN,
        "default_denominator": len(scenarios),
        "profiles": {
            profile: len([row for row in scenarios if row["profile"] == profile])
            for profile in ("perl-default", "python-default", "vpi-linux-default")
        },
        "types": dict(collections.Counter(row["effective_type"] for row in scenarios)),
        "eligible_denominator": len(eligible),
        "tracked_fixture_files": len(inputs),
        "no_compiler_or_model_was_executed": True,
        "optional_profiles_are_not_included_or_certified": True,
        "historical_results_are_not_new_run_credit": True
    }
    assert summary["profiles"] == {
        "perl-default": 3028,
        "python-default": 746,
        "vpi-linux-default": 76
    }
    assert len(scenarios) == 3850 and len(eligible) == 2209 and len(inputs) == 6090
    outputs = {
        "core-inventory.json": scenarios,
        "first128-runtime-structural.json": selection,
        "first256-runtime-structural.json": selection256,
        "all-tracked-ivtest-inputs.json": inputs,
        "parser-state-comparisons.json": comparisons,
        "raw-lists.json": raw_lists,
        "summary.json": summary
    }
    for name, data in outputs.items():
        with (args.out / name).open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    recovery = {
        "prior_core_sha256": PRIOR_CORE_SHA,
        "prior_selection_sha256": PRIOR_SELECTION_SHA,
        "regenerated_core_sha256": digest(args.out / "core-inventory.json")["sha256"],
        "regenerated_selection_sha256":
        digest(args.out / "first128-runtime-structural.json")["sha256"],
        "prior_uncommitted_files_and_logs_were_not_restored": True
    }
    recovery["same_selection_bytes"] = recovery[
        "regenerated_selection_sha256"] == PRIOR_SELECTION_SHA
    recovery["same_core_metadata_bytes"] = recovery["regenerated_core_sha256"] == PRIOR_CORE_SHA
    with (args.out / "RECOVERY_COMPARISON.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(recovery, indent=2) + "\n")
    print(json.dumps({**summary, "recovery": recovery}, indent=2))


if __name__ == "__main__":
    main()
