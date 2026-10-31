# Withdrawn clocking expectations

Upstream [PR #8925](https://github.com/verilator/verilator/pull/8925) removed these
five files in `c0b2894994ce468303b79e8ef901f633dd134f00`. They are retained here
unchanged, outside automatic `test_regress/t/t_*.py` discovery. The manifest pins
the upstream blobs, exact file bytes, executable modes, and original 438-driver
selection in the order used by base427 `build.bash`.

`historical-427/` contains unmodified native receipts and deterministic gzip
copies of the raw local427 failure logs. The manifest distinguishes those local
observations from [PR #44's CI run](https://github.com/Mafei/verilator/actions/runs/41149106649)
and records exact historical core artifact hashes. Historical results never
provide validation credit for a later commit.

Run `python3 ci/portable/clocking_legacy.py run --repo CHECKOUT --compiler
CHECKOUT/bin/verilator_bin --output CHECKOUT/out/clocking-legacy` to replay both
original drivers sequentially with an owned scratch harness. The checkout's
canonical test directory is never modified. Retained receipts observe the real
harness child, not a separately observed compiler/model child. Each expected
harness failure remains exit10/raw2560, 0 passed and 1 failed. Their combined
original criteria remain false, with derived aggregate returncode1 and 0 passed/2
failed; returncode1 is not claimed as a separately observed native process.
`audit` with `--repo` and `--output` recomputes evidence without trusting
saved `audit.json`; successful verification returns0 only for this separate audit.

`INAPPLICABLE_REVERTED_CONTRACT` describes withdrawn expectations. It is not a
semantic pass and does not change global HOLD. The original 438-driver projection
must combine the unchanged remaining436 results with these two raw failures.
The revised applicable selection is reported separately.

Passive input rvalues, driving input nets subject to coercion/support, and output
lvalues need distinct coverage. The historical [Accellera assignment-pattern
ballot](https://www.accellera.org/images/eda/sv-bc/att-8284/P1800_ballot_issue_226_275.htm)
permits positional pattern lvalues; it does not justify treating all output
patterns as illegal. Current IEEE full text was not independently obtained.
