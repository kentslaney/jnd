"""Tests for prepare_audio.py."""

import os
from unittest import mock

import numpy as np
import scipy.io.wavfile
from absl.testing import absltest

import prepare_audio


class PrepareAudioTest(absltest.TestCase):

    def setUp(self):
        super().setUp()
        self.temp_dir = self.create_tempdir()
        self.fs = 16000
        
        # 1. Generate Synthetic Audio: 5s silence + 1s tone + 5s silence
        self.silence_len = 5
        self.tone_len = 1
        
        silence_samples = self.silence_len * self.fs
        tone_samples = self.tone_len * self.fs
        
        # Create a 440 Hz sine wave tone
        t = np.linspace(0, self.tone_len, tone_samples, endpoint=False)
        tone = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)
        
        # Create pure silence
        silence = np.zeros(silence_samples, dtype=np.int16)
        
        # Concatenate into the final 11-second test array
        self.test_audio = np.concatenate([silence, tone, silence])
        self.total_len_seconds = self.silence_len * 2 + self.tone_len

    def test_frame_energy(self):
        """Tests that energy is correctly calculated across the audio frames."""
        energy, hop_length = prepare_audio.frame_energy(self.test_audio)
        
        self.assertEqual(hop_length, 512)
        
        # Check that the start and end of the energy array are zero (silence)
        self.assertEqual(energy[0], 0)
        self.assertEqual(energy[-1], 0)
        
        # Check that the middle of the array detected the tone's energy
        self.assertGreater(max(energy), 0)

    @mock.patch('prepare_audio.plt')
    def test_endpoint_audio(self, mock_plt):
        """Tests that the leading silence is removed, respecting the 20-frame pad."""
        energy, hop_length = prepare_audio.frame_energy(self.test_audio)
        
        trimmed_audio = prepare_audio.endpoint_audio(
            self.test_audio, energy, self.fs, hop_length
        )
        
        # The tone starts at sample 80,000.
        # Frame 155 starts at 79,360 and ends at 80,384 (width 1024).
        # It is the first frame to overlap the tone, triggering the threshold.
        # Target loc = 155 - 20 (pad) = 135.
        # Trim starts at 135 * 512 = 69,120.
        # Expected remaining samples: 176,000 - 69,120 = 106,880.
        expected_length = 106880
        
        self.assertEqual(len(trimmed_audio), expected_length)
        
        # Verify that the hardcoded plot calls don't fire a real window
        self.assertTrue(mock_plt.plot.called)
        self.assertTrue(mock_plt.axhline.called)
        self.assertTrue(mock_plt.axvline.called)

    @mock.patch('prepare_audio.read_mp4')
    @mock.patch('prepare_audio.plt')
    def test_process_all_files(self, mock_plt, mock_read_mp4):
        """Integration test for the file loop, mocking ffmpeg."""
        
        # Create a dummy file without an mp4 extension so it bypasses skip_suffixes
        dummy_base_name = 'sin_test_recording'
        dummy_file_path = os.path.join(self.temp_dir.full_path, dummy_base_name)
        with open(dummy_file_path, 'w') as f:
            f.write('dummy metadata')
            
        # Mock read_mp4 to return our synthetic audio instead of calling ffmpeg
        mock_read_mp4.return_value = (self.fs, self.test_audio)
        
        # Run the processing pipeline
        prepare_audio.process_all_files(
            directory=self.temp_dir.full_path, 
            pattern='sin*'
        )
        
        # Verify the output wav file was successfully created
        expected_output_path = dummy_file_path + '.wav'
        self.assertTrue(os.path.exists(expected_output_path))
        
        # Read the file back from disk to verify it contains the trimmed audio
        rate, data = scipy.io.wavfile.read(expected_output_path)
        self.assertEqual(rate, self.fs)
        
        # Ensure it was actually trimmed compared to the original 11s array
        self.assertLess(len(data), len(self.test_audio))


if __name__ == '__main__':
    absltest.main()
