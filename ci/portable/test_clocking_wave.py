#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require the clocking evidence checker to reject timing and source corruption."""

import copy
import gzip
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import clocking_wave

FIXTURE = Path(__file__).with_name('fixtures') / 'clocking_connections.vcd.gz'
WAVE_SHA256 = '021855ca6c0dc62f6d6e813c747a5c7ca9eec3b808c8a4eeba4c92e72360fe78'


class ClockingWaveTest(unittest.TestCase):
    """Mutate independently captured compiler output; never alter the HDL oracle."""

    @classmethod
    def setUpClass(cls):
        cls.wave = gzip.decompress(FIXTURE.read_bytes())
        if hashlib.sha256(cls.wave).hexdigest() != WAVE_SHA256:
            raise ValueError('Captured baseline waveform changed')

    def test_original_capture(self):
        self.assertEqual(clocking_wave.verify(self.wave), 426)

    def test_output_at_event_is_rejected(self):
        with self.assertRaises(ValueError):
            clocking_wave.verify(self.wave.replace(b'#15001\n', b'#15000\n'))

    def test_output_two_ps_late_is_rejected(self):
        with self.assertRaises(ValueError):
            clocking_wave.verify(self.wave.replace(b'#15001\n', b'#15002\n'))

    def test_zero_output_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clocking_value'):
            clocking_wave.verify(self.wave.replace(b'#16002\n', b'b0 /\n#16002\n', 1))

    def test_passive_source_write_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clocking_value'):
            clocking_wave.verify(self.wave.replace(b'#16002\n', b'b0 "\n#16002\n', 1))

    def test_unknown_output_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clocking_unknown_value'):
            clocking_wave.verify(self.wave.replace(b'#16002\n', b'bx /\n#16002\n', 1))

    def test_missing_cycle_is_rejected(self):
        begin = self.wave.index(b'#15001\n')
        end = self.wave.index(b'#16002\n', begin)
        with self.assertRaisesRegex(ValueError, 'clocking_missing_observation'):
            clocking_wave.verify(self.wave[:begin] + self.wave[end:])

    def test_truncated_wave_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clocking_truncated_wave'):
            clocking_wave.verify(self.wave[:self.wave.index(b'#85000\n')])

    def test_wrong_timescale_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clocking_timescale'):
            clocking_wave.verify(self.wave.replace(b'1ps', b'1ns', 1))

    def test_reversed_time_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clocking_time_reversed'):
            clocking_wave.verify(self.wave.replace(b'#15001\n', b'#1\n', 1))

    def test_record_and_missing_model_log(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            objects = root / 'test_regress/obj_vlt/t_clocking_port_connections'
            objects.mkdir(parents=True)
            (objects / 'simx.vcd').write_bytes(self.wave)
            log = b''.join(b'settled cycle=%d\n' % i for i in range(8))
            (objects / 'vlt_sim.log').write_bytes(log + b'*-* All Finished *-*\n')
            (root / 'bin').mkdir()
            (root / 'bin/verilator_bin').write_bytes(b'captured compiler identity')
            with patch.object(clocking_wave.subprocess, 'check_output', return_value='a' * 40):
                report = clocking_wave.validate(root)
                self.assertEqual(clocking_wave.core_fields(report), report)
                (objects / 'vlt_sim.log').unlink()
                with self.assertRaisesRegex(ValueError, 'clocking_missing_regular_file'):
                    clocking_wave.validate(root)

    def test_false_typed_credit_is_rejected(self):
        report = {
            'schema': 'clocking-wave-v1',
            'head': 'a' * 40,
            'compiler_sha256': 'b' * 64,
            'wave_sha256': WAVE_SHA256,
            'sim_log_sha256': 'c' * 64,
            'cycles': 8,
            'checks': 426,
            'output_skew_ps': 1,
            'semantic_pass': True
        }
        for field, value in (('checks', True), ('checks', 425), ('cycles', 7),
                             ('output_skew_ps', 0), ('semantic_pass', False),
                             ('wave_sha256', 'unknown'), ('head', 'wrong')):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(report)
                changed[field] = value
                with self.assertRaises(ValueError):
                    clocking_wave.core_fields(changed)


if __name__ == '__main__':
    unittest.main()
