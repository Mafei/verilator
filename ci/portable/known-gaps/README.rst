Public known gaps
=================

These inputs preserve independently observed gaps. They are not counted as
passing runtime regressions and do not redefine legal SystemVerilog as invalid.
The complete-simulator and full-vendor-model claims remain out of scope; see
../SV_SCOPE.rst and the exact-SHA native acceptance artifacts.

wait_fourstate_reduction.sv
---------------------------

The original observation arose while creating an independent wildcard test.
A four-state reduction in ``wait (&state)`` was captured before the suspension
and failed to reevaluate after state changed. The wildcard regression uses an
explicit deadline and exact worker completion checks, preserving all 2570
operator assertions; the separate wait failure is retained here.

Observed on the October26 working compiler before final-SHA validation:
Verilator compile0/run1; pinned Icarus f45ffabe compile0/run0. Raw native waits
and unfiltered logs are in cloud evidence wait-reduction-gap-v1. Reproduce::

    bin/verilator --binary --fourstate -Wno-FUTURE --top-module t \
      --Mdir /tmp/wait-model ci/portable/known-gaps/wait_fourstate_reduction.sv
    /tmp/wait-model/Vt

The SV source asserts that the wait resumed before the fixed deadline, so a
model that merely exits zero without the expected behavior cannot pass.

Other explicit boundaries
-------------------------

The earlier W4 runtime-index ``+:33`` width invariant is preserved in the old
failure evidence. The general positioned-write repair also removed its compile
failure. The ordinary/four-state clipped-write regression now includes that
33-bit selection directly at W4 as well as the 63/65/95-bit profiles; there is
no narrower W4 exception. Its actual runtime/history acceptance must still be
read from the matching final-SHA result.

Nested unpacked structures with XZ fields remain explicitly unsupported, with
an original-harness diagnostic regression. No X/Z expectation was changed to
zeros to label that profile as supported.
