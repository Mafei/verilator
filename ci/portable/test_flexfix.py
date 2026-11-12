#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""The selected GNU header has int signatures even on macOS Tahoe."""
import io
import runpy
import sys
from contextlib import redirect_stdout
from unittest.mock import patch

source = 'int yyFlexLexer::LexerInput(char* buf, int max_size) {\nint yyFlexLexer::LexerOutput(const char* buf, int size) {\n'
for lexer in ('V3Lexer', 'V3PreLex'):
    for system, version in [('Darwin', '26.6.2'), ('Darwin', '15.0'), ('Linux', '')]:
        result = io.StringIO()
        with (
                patch('platform.system', return_value=system),
                patch('platform.mac_ver', return_value=(version, ('', '', ''), '')),
                patch.object(sys, 'argv', ['src/flexfix', lexer]),
                patch.object(sys, 'stdin', io.StringIO(source)),
                redirect_stdout(result),
        ):
            runpy.run_path('src/flexfix', run_name='__main__')
        assert result.getvalue() == source, (lexer, system, result.getvalue())

# Flex 2.6.5 changes the C preprocessor lexer's debug symbol. The C++ lexer
# and identifiers containing that spelling must remain unchanged.
source = 'int yyflexdebug;\nint not_yyflexdebug;\n'
for lexer, expected in [('V3Lexer', source),
                        ('V3PreLex', 'int yy_flex_debug;\nint not_yyflexdebug;\n')]:
    result = io.StringIO()
    with (
            patch.object(sys, 'argv', ['src/flexfix', lexer]),
            patch.object(sys, 'stdin', io.StringIO(source)),
            redirect_stdout(result),
    ):
        runpy.run_path('src/flexfix', run_name='__main__')
    assert result.getvalue() == expected, (lexer, result.getvalue())
