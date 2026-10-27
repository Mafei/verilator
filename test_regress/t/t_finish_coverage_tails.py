#!/usr/bin/env python3
# DESCRIPTION: Verilator: Nested finish counters and normal task return
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from finish_cov_tail_common import run_public

test.scenarios('vlt')
run_public(test, 'tails')
test.passes()
