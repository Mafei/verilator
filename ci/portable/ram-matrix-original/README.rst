Original public six-lane RAM matrix
===================================

This is the unchanged public matrix used with PR20, not a vendor model.
The source SHA256 is
``43aa01a03b7924890866569a0973a955026ec458c2c6fb11dbef009c965dd2e3``.
It checks 318 assertions, 84 literal reports and 30 complete signal histories
for 7-, 33- and 65-bit values in both range directions. The original oracle
execution code is unchanged; only SPDX comments were added for repository use.

Run ``python3 ci/portable/ram_acceptance.py`` after building this checkout.
All three original compile/build/run commands must exit zero before the
unchanged whole-history oracle is run. Receipts, logs, wave and result live
in ``out/ram-matrix/original``; a failed stage stops acceptance.
This bounded matrix is not full SystemVerilog certification.
