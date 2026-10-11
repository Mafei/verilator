Original public finish controls
==============================

These four CC0 inputs are preserved byte for byte from the 2026-10-09 public
termination controls. ``finish_acceptance.py`` checks their SHA-256 manifest and
extracts only the original oracle functions; it does not run either historical
Python script. Those scripts retain historical local paths and a generated-code
diagnostic solely as provenance. No diagnostic modification is applied to a
candidate compiler or model.

All nine profiles execute with independent compile, build, and model receipts.
The original case 5 still requires ``FINAL 5 1 q=0`` and forbids every
``UNREACHABLE`` line. This remains the original strict criterion, with no claim
that its same-region termination ordering is certified by IEEE 1800.
An actual zero model exit cannot turn differing output into a semantic pass.

The checker publishes the full raw model output and full VCD contents in
``FINISH9_CASE`` console records. All native receipts, model logs, original
inputs, and waveforms are retained under ``out/finish9/`` in the CI artifact.
