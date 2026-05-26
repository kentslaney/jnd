"""Tests for score_and_report.py."""

import json
import os
import sqlite3
from unittest import mock

import numpy as np
from absl.testing import absltest
from absl.testing import flagsaver
from absl import flags

import score_and_report

FLAGS = flags.FLAGS


class ScoreAndReportTest(absltest.TestCase):

    def setUp(self):
        super().setUp()
        # Create a temporary directory to isolate file creation during tests
        self.temp_dir = self.create_tempdir()
        
        # Setup file paths
        self.db_path = os.path.join(self.temp_dir.full_path, 'test.db')
        self.homonyms_path = os.path.join(self.temp_dir.full_path, 'homonyms.csv')
        self.csv_out_path = os.path.join(self.temp_dir.full_path, 'out.csv')
        self.html_out_path = os.path.join(self.temp_dir.full_path, 'discrepancies.html')
        
        # Create a mock homonym CSV
        with open(self.homonyms_path, 'w') as f:
            f.write("# Comment line\n")
            f.write("there, their, they're\n")
            f.write("bear, bare\n")
            f.write("  \n") # Empty line
            
        self._create_mock_database(self.db_path)

    def _create_mock_database(self, db_path):
        """Creates an actual SQLite DB in the temp dir and seeds it with test cases."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Create Schema
        cursor.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, ip TEXT, t TEXT);
            CREATE TABLE user_info (user INTEGER, info_key TEXT, value TEXT, t TEXT);
            CREATE TABLE audio_trials (id INTEGER PRIMARY KEY, project TEXT, snr INTEGER, lang TEXT, level_number INTEGER, trial_number INTEGER, filename TEXT, answer TEXT, active BOOLEAN);
            CREATE TABLE audio_results (id INTEGER PRIMARY KEY, subject INTEGER, trial INTEGER, reply_filename TEXT, t TEXT);
            CREATE TABLE audio_asr (ref INTEGER PRIMARY KEY, data TEXT, gt_word_count INTEGER, correct_word_count INTEGER, asr_clean_tokens TEXT);
            CREATE TABLE audio_annotations (ref INTEGER PRIMARY KEY, data TEXT);
        """)

        # 2. Seed Data
        # User 1: Normal user
        cursor.execute("INSERT INTO users VALUES (1, 'A1S1', '127.0.0.1', '2023-01-01')")
        # User 2: Needs to be fixed by fix_random_user_names
        cursor.execute("INSERT INTO users VALUES (2, 'DFe3RNee', '127.0.0.1', '2023-01-01')")
        # User 3: Skipped user
        cursor.execute("INSERT INTO users VALUES (3, 'A1P8', '127.0.0.1', '2023-01-01')")

        # Assign test-type to users
        for i in range(1, 4):
            cursor.execute(f"INSERT INTO user_info VALUES ({i}, 'test-type', 'pilot', '2023-01-01')")

        # Trials
        # Trial 1: Exact match scenario
        cursor.execute("INSERT INTO audio_trials VALUES (1, 'quicksin', 10, 'en', 1, 1, 'file1', 'hello world', 1)")
        # Trial 2: Homonym and '/' option scenario
        cursor.execute("INSERT INTO audio_trials VALUES (2, 'azbio', 5, 'en', 1, 2, 'file2', 'the bare/bear necessity', 1)")
        # Trial 3: Invalid JSON target
        cursor.execute("INSERT INTO audio_trials VALUES (3, 'quicksin', 0, 'en', 1, 3, 'file3', 'should fail', 1)")

        # Results
        cursor.execute("INSERT INTO audio_results VALUES (101, 1, 1, 'rep1', '2023-01-01')") # Normal user, Trial 1
        cursor.execute("INSERT INTO audio_results VALUES (102, 2, 2, 'rep2', '2023-01-01')") # Random user, Trial 2
        cursor.execute("INSERT INTO audio_results VALUES (103, 3, 1, 'rep3', '2023-01-01')") # Skipped user, Trial 1
        cursor.execute("INSERT INTO audio_results VALUES (104, 1, 3, 'rep4', '2023-01-01')") # Normal user, Trial 3

        # ASR Data
        valid_asr_1 = json.dumps({"text": "Hello world", "segments": [{"words": [{"word": "Hello", "start": 0.1}, {"word": "world", "start": 0.5}]}]})
        valid_asr_2 = json.dumps({"text": "The bear necessity", "segments": [{"words": [{"word": "The"}, {"word": "bear"}, {"word": "necessity"}]}]})
        
        cursor.execute("INSERT INTO audio_asr (ref, data) VALUES (101, ?)", (valid_asr_1,))
        cursor.execute("INSERT INTO audio_asr (ref, data) VALUES (102, ?)", (valid_asr_2,))
        cursor.execute("INSERT INTO audio_asr (ref, data) VALUES (103, ?)", (valid_asr_1,))
        cursor.execute("INSERT INTO audio_asr (ref, data) VALUES (104, 'INVALID { JSON [')") # Corrupted JSON

        # Annotations (Audiologist judgements)
        cursor.execute("INSERT INTO audio_annotations VALUES (101, '[true, true]')") # Agrees with ASR
        cursor.execute("INSERT INTO audio_annotations VALUES (102, '[true, false, true]')") # Disagrees with ASR (creates discrepancy)
        
        conn.commit()
        conn.close()

    def test_clean_and_tokenize(self):
        self.assertEqual(score_and_report.clean_and_tokenize(None), set())
        self.assertEqual(score_and_report.clean_and_tokenize(""), set())
        self.assertEqual(
            score_and_report.clean_and_tokenize("Hello, World! This is a test."),
            {"hello", "world", "this", "is", "a", "test"}
        )

    def test_fix_random_user_names(self):
        self.assertEqual(score_and_report.fix_random_user_names("DFe3RNee"), "A0S1")
        self.assertEqual(score_and_report.fix_random_user_names("NQE7QNNm"), "A0S1")
        self.assertEqual(score_and_report.fix_random_user_names("mMD4mHfH"), "A0S2")
        self.assertEqual(score_and_report.fix_random_user_names("QA7D33Nr"), "A0S3")
        self.assertEqual(score_and_report.fix_random_user_names("A1S5"), "A1S5") # Unchanged

    def test_fix_encoding(self):
        # Normal string
        self.assertEqual(score_and_report.fix_encoding("hello"), "hello")
        # Ensure it falls back and replaces correctly on bad mojibake
        encoded = score_and_report.fix_encoding("café")
        self.assertIn("caf&#233;", encoded) 

    def test_load_homonyms(self):
        # Test successful load
        homonyms = score_and_report.load_homonyms(self.homonyms_path)
        self.assertIn("there", homonyms)
        self.assertIn("their", homonyms["they're"])
        self.assertIn("bear", homonyms["bare"])
        
        # Test missing file (should not crash, just warn and return empty dict)
        empty_homonyms = score_and_report.load_homonyms("does_not_exist.csv")
        self.assertEqual(empty_homonyms, {})

    def test_accumulate_errors(self):
        sum_arr = np.zeros((2, 2), dtype=int)
        human = [True, False, True, False]
        asr = [True, True, False, False]
        
        score_and_report.accumulate_errors(sum_arr, human, asr)
        
        # [0, 0] = False, False -> 1
        # [0, 1] = False, True  -> 1
        # [1, 0] = True, False  -> 1
        # [1, 1] = True, True   -> 1
        self.assertEqual(sum_arr[0, 0], 1)
        self.assertEqual(sum_arr[0, 1], 1)
        self.assertEqual(sum_arr[1, 0], 1)
        self.assertEqual(sum_arr[1, 1], 1)

    @mock.patch('score_and_report.plt.savefig')
    def test_main_integration(self, mock_savefig):
        """Tests the main pipeline end-to-end to ensure DB writes and files are generated."""
        
        # Override flags to point to our isolated temp files
        with flagsaver.flagsaver(
            dbfile=self.db_path,
            homonyms=self.homonyms_path,
            discrepancies=self.html_out_path,
            subject_filter='A\\d+[SP]\\d+'
        ):
            # Change working directory so CSVs/Plots generate in temp_dir
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir.full_path)
            
            try:
                # Run the main program
                score_and_report.main([])
                
                # 1. Verify DB Updates
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT ref, gt_word_count, correct_word_count FROM audio_asr ORDER BY ref")
                rows = cursor.fetchall()
                conn.close()
                
                # Ref 101: 2 GT words, 2 Correct
                self.assertEqual(rows[0][1], 2)
                self.assertEqual(rows[0][2], 2)
                
                # Ref 102: 3 GT words, 3 Correct (Handled 'bare/bear' homonym correctly)
                self.assertEqual(rows[1][1], 3)
                self.assertEqual(rows[1][2], 3)
                
                # Ref 103 (Skipped user) and 104 (Bad JSON) should have NULLs
                self.assertIsNone(rows[2][1])
                self.assertIsNone(rows[3][1])

                # 2. Verify Output Files
                self.assertTrue(os.path.exists('quicksin_results.csv'))
                self.assertTrue(os.path.exists(self.html_out_path))
                
                # 3. Verify Matplotlib savefig was called
                mock_savefig.assert_called_once_with('confusion_matrices.png')
                
            finally:
                # Restore original directory
                os.chdir(original_cwd)

    def test_main_missing_db(self):
        """Ensures the program catches a missing DB file."""
        with flagsaver.flagsaver(dbfile="non_existent_db.db"):
            with self.assertRaises(AssertionError) as context:
                score_and_report.main([])
            self.assertIn("does not exist", str(context.exception))

if __name__ == '__main__':
    absltest.main()
