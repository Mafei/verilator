#!/usr/bin/env python3
# DESCRIPTION: Verilator: Four-state event-controlled NBA concat capture
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import runpy

import vltest_bootstrap

test.scenarios('vlt')
runpy.run_path('t/t_timing_nba_event_concat.py', globals())
