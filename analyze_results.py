import csv
from dataclasses import dataclass
import json
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import ArrayLike, NDArray
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import sqlite3


def get_all_sql_data(database: str = 'experiments.db'):
  con = sqlite3.connect(database)
  print(type(con))
  cur = con.cursor()
  query = """SELECT * FROM audio_results
    LEFT JOIN audio_trials ON audio_results.trial=audio_trials.id
    LEFT JOIN users ON subject=users.id
    LEFT JOIN (select * from user_info where info_key='test-type' group by user)
                as 'user_info' ON users.id=user_info.user
    LEFT JOIN audio_asr ON audio_results.id=audio_asr.ref
    LEFT JOIN audio_annotations ON audio_results.id=audio_annotations.ref
    where info_key='test-type'
    """
  all_query_results = cur.execute(query).fetchall()
  return all_query_results


def get_all_test_transcripts(database: str = 'experiments.db'):
  con = sqlite3.connect(database)
  print(type(con))
  cur = con.cursor()
  query = """SELECT * FROM audio_trials
          """
  all_query_results = cur.execute(query).fetchall()
  return all_query_results


def fix_random_user_names(text_tag: str) -> str:
  match text_tag:
    case 'DFe3RNee' | 'NQE7QNNm':
      return 'A0S1' # Emily'
    case 'mMD4mHfH':
      return 'A0S2' # 'Varsha'
    case 'QA7D33Nr':
      return 'A0S3' # 'Shreyas'
  return text_tag


@dataclass
class QS_result:
  """This dataclass contains everything that we retrieve from the web database
  to describe one QuickSIN sentence trial.  It contains information about the s
  ubject, the trial (list and sentence number), and the ASR results (as computed
  on the server). We extend it to say if the audioloigist and the ASR systems
  match.

  Note: These fields must be in the same order as the SQL query above.
  """
  results_id: int
  results_subject: int
  results_trial: int
  results_reply_filename: str
  # results_reply_asr: str
  results_time: str              # quick_results
  trials_id: int
  trials_project: str            # Type of test (qs, azbio, etc)
  trials_snr: int
  trials_lang: str
  trials_level_number: int # The qs sentence number (1 based)
  trials_trial_number: int # The qs list number (1 based)
  trials_filename: str # Which sound file was played
  trials_answer: str # Comma separated list of true words
  trials_active: bool  # ???
  user_id: int
  user_name: str # Audiologist#Subject#
  user_ip: str
  user_time: str # users
  user_info_id: int
  user_info_key: str # What kind of info: searchParams or test-type?
  user_info_value: str
  user_info_time: str
  asr_id: int
  # asr_ref: int
  asr_results: Union[str, Dict[str, Any]]  # json encoded asr results
  annotation_ref: int
  annotation_matches: Union[str, List[bool]] # quick_annotations (human labels)
  asr_words: Optional[List[str]] = None  # List of all words recognized by ASR
  asr_matches: Optional[List[bool]] = None # Whether ASR found the keyword
  asr_times: Optional[List[float]] = None # The starting time for each matched word
  audiology_asr_matches: Optional[List[bool]] = None


def normalize_word(word: str) -> str:
  """Remove all but the letters in a word."""
  return re.sub(r'[^\w]', '', word.lower())

def normalize_results(a_result: QS_result):
  a_result.user_name = fix_random_user_names(a_result.user_name)
  if isinstance(a_result.asr_results, str):
    a_result.asr_results = json.loads(a_result.asr_results)

  if isinstance(a_result.annotation_matches, str):
    a_result.annotation_matches = json.loads(a_result.annotation_matches)

  if isinstance(a_result.trials_answer, str):
    a_result.trials_answer = a_result.trials_answer.split(',')

  # Split recognition into a list of words
  a_result.asr_words = []
  if (a_result.asr_results and 'segments' in a_result.asr_results and
      a_result.asr_results['segments'] and
      'words' in a_result.asr_results['segments'][0]):
    # Remove punctation and spaces to normalize ASR results
    a_result.asr_words = [normalize_word(w['word'])
                          for w in a_result.asr_results['segments'][0]['words']]
  return a_result


def score_asr_system(a_result: QS_result,
                     all_ground_truth: Dict[Tuple[str, int, int], str],
                     debug: bool = False):
  # Score the ASR results, creating a list of true/false
  # ground_truth = all_keyword_dict[(a_result.trials_trial_number-1,
  #                                  a_result.trials_level_number-1)]
  ground_truth = all_ground_truth[(a_result.trials_project,
                                   a_result.trials_trial_number,
                                   a_result.trials_level_number)]
  word_matches = []
  match_times = []
  # Parse the JSON result, if we haven't already done that.
  if isinstance(a_result.asr_results, str):
    a_result.asr_results = json.loads(a_result.asr_results)
  if isinstance(a_result.annotation_matches, str):
    a_result.annotation_matches = json.loads(a_result.annotation_matches)
  # Check if segments exist and contain words
  if (a_result.asr_results and 'segments' in a_result.asr_results and
      a_result.asr_results['segments'] and
      'words' in a_result.asr_results['segments'][0]):
    for ground_truth_set in ground_truth:
      for reco in a_result.asr_results['segments'][0]['words']:
        word = normalize_word(reco['word'])
        if word in ground_truth_set:
          word_matches.append(True)
          match_times.append(reco['start'])
          break
      else:
        word_matches.append(False)
        match_times.append(np.nan)
  else:
    # Handle cases where segments or words are missing
    # For example, you could set all matches to False and times to NaN
    word_matches = [False] * len(ground_truth)
    match_times = [np.nan] * len(ground_truth)
  if debug:
    print(f'Want these words: {ground_truth}')
    print(f'   in ASR results: {a_result.asr_words}')
    print(f'   results: {word_matches} at {match_times}s')
  a_result.asr_matches = word_matches
  a_result.asr_times = match_times


def score_matches(a_result: QS_result, debug: bool = False):
  """Compare the audilogy and ASR annotations.
  """
  matches = [not(a ^ b) for a,b in zip(a_result.asr_matches, a_result.annotation_matches)]
  if debug:
    print(a_result.asr_matches, a_result.annotation_matches, matches)
  a_result.audiology_asr_matches = matches



def convert_sql_to_results(all_query_results,
                           all_ground_truth) -> List[QS_result]:
  #Convert the SQL database into a list of qs_result objects
  debug_test_count = {}
  all_results = []
  no_asr_results = 0
  for db_result in all_query_results: # Iterate through SQL responses
    a_result = QS_result(*db_result)
    if a_result.asr_results is None:
      no_asr_results += 1
      continue
    # if a_result.trials_project != 'quick':
    #   not_quick_tests += 1
    # else:
    if True:
      test_name = a_result.trials_project
      if test_name not in debug_test_count:
        debug_test_count[test_name] = 0
      debug_test_count[test_name] += 1
      # print(test_name, debug_test_count[test_name])

      normalize_results(a_result)
      # if not a_result.user_name.startswith('A'):
      #   continue
      if a_result.user_name in ['A1P8', 'A1P9', 'A2P15']:
        print(f'Skipping user {a_result.user_name} for not following directons')
        continue
      # if a_result.user_info_value != 'pilot':
      #   continue
      score_asr_system(a_result, all_ground_truth, 
                       debug_test_count[test_name] < 3)
      score_matches(a_result, debug_test_count[test_name] < 3)
    all_results.append(a_result)
  return all_results


def save_results_as_csv(all_results: List[QS_result],
                        csv_file: str = 'quicksin_results.csv') -> str:

  # Define the header row based on the QS_result dataclass fields you want to include
  header = [
      'results_id', 'results_subject', 'results_trial', 'results_reply_filename',
      'results_time', 'trials_id', 'trials_project', 'trials_snr', 'trials_lang',
      'trials_level_number', 'trials_trial_number', 'trials_filename',
      'trials_answer', 'trials_active', 'user_id', 'user_name', 'user_ip',
      'user_time', 'user_info_id', 'user_info_key', 'user_info_value',
      'user_info_time', 'asr_id', 'asr_results', 'annotation_ref',
      'annotation_matches', 'asr_words', 'asr_matches', 'asr_times',
      'audiology_asr_matches'
  ]

  # Write the data to the CSV file
  with open(csv_file, 'w', newline='') as f:
      writer = csv.writer(f)
      writer.writerow(header)  # Write the header row
      for result in all_results:
          row_data = [
              result.results_id, result.results_subject, result.results_trial,
              result.results_reply_filename, result.results_time,
              result.trials_id, result.trials_project, result.trials_snr,
              result.trials_lang, result.trials_level_number,
              result.trials_trial_number, result.trials_filename,
              # Join list fields into strings for CSV compatibility
              ','.join(result.trials_answer) if isinstance(result.trials_answer, list) else result.trials_answer,
              result.trials_active, result.user_id, result.user_name, result.user_ip,
              result.user_time, result.user_info_id, result.user_info_key,
              result.user_info_value, result.user_info_time, result.asr_id,
              json.dumps(result.asr_results), # Convert dict to JSON string
              json.dumps(result.annotation_matches), # Convert list to JSON string
              ','.join(result.asr_words) if isinstance(result.asr_words, list) else result.asr_words,
              ','.join([str(m) for m in result.asr_matches]) if isinstance(result.asr_matches, list) else result.asr_matches,
              ','.join([str(t) for t in result.asr_times]) if isinstance(result.asr_times, list) else result.asr_times,
              ','.join([str(m) for m in result.audiology_asr_matches]) if isinstance(result.audiology_asr_matches, list) else result.audiology_asr_matches
          ]
          writer.writerow(row_data)

  print(f'Results written to {csv_file}')
  return csv_file


def accumulate_errors(sum: NDArray, human: ArrayLike, asr: ArrayLike) -> None:
  assert sum.ndim == 2
  assert sum.shape == (2, 2)
  for h, a in zip(human, asr):
    sum[int(h), int(a)] += 1

# sum = np.zeros((2, 2), dtype=int)
# accumulate_errors(sum, [True, False], [True, True])
# sum


def all_test_confusions(all_results: List[QS_result]) -> Dict[str, NDArray]:
  """Create a dictionary of confusion matrices, one per test type.
  Each confusion matrix is indexed by
    human, asr
  """
  valid_subject_re = re.compile('A\d+[SP]\d+')
  all_confusions = {}
  for r in all_results:
    if valid_subject_re.match(r.user_name):
      test_name = r.trials_project
      if test_name not in all_confusions:
        all_confusions[test_name] = np.zeros((2, 2), dtype=int)
      accumulate_errors(all_confusions[test_name],
                        r.annotation_matches, r.asr_matches)
  return all_confusions

# all_confusions = all_test_confusions(all_results)
# all_confusions


def plot_confusions(all_confusions: Dict[str, NDArray]):
  centers = [0, 1]
  for i, test_name in enumerate(all_confusions.keys()):
    plt.subplot(2, 3, i+1)
    confusions = all_confusions[test_name]
    plt.imshow(confusions)
    for human_match in [0, 1]:
      for asr_match in [0, 1]:
        plt.text(centers[human_match], centers[asr_match], 
                confusions[human_match, asr_match],
                ha="center", va="center", color="w")
    plt.title(test_name)
    if i == 0 or i == 3:
      plt.ylabel('Human')
      plt.yticks([0, 1], ['False', 'True'])
    else:
      plt.yticks([])
    if i >= 3:
      plt.xlabel('ASR')
      plt.xticks([0, 1], ['False', 'True'])
    else:
      plt.xticks([])
  plt.tight_layout()


def generate_html_report(all_results: List[QS_result],
                         all_ground_truth: Dict[Tuple[str, int, int], str],
                         only_discrepancies: bool = True,
                         filter_tests: List[str] = None,
                         max_number: int = 10000000000) -> Tuple[str, int]:
  # Generate an HTML report of the inconsistencies
  html_output = """
  <!DOCTYPE html>
  <html>
  <head>
  <title>QuickSIN ASR vs Audiologist Discrepancies</title>
  <style>
    table {
      border-collapse: collapse;
      width: 100%;
    }
    th, td {
      border: 1px solid #dddddd;
      text-align: left;
      padding: 8px;
    }
    th {
      background-color: #f2f2f2;
    }
    .discrepancy {
      background-color: #ffcccc;
    }
  </style>
  </head>
  <body>

  <h1>QuickSIN ASR vs Audiologist Discrepancies</h1>

  <table>
    <tr>
      <th>Subject</th>
      <th>Test Type</th>
      <th>List Number</th>
      <th>Sentence Number</th>
      <th>Ground Truth</th>
      <th>ASR Words</th>
      <th>Audiologist Matches</th>
      <th>ASR Matches</th>
      <th>Agree</th>
      <th>Subject Audio</th>
    </tr>
  """

  valid_subject_re = re.compile('A\d+[PS]\d+')
  row_count = 0
  for result in all_results[:max_number]:
    if not valid_subject_re.match(result.user_name):
      continue
    if filter_tests and result.trials_project not in filter_tests:
      continue
    # Check if there's any disagreement between audiology_asr_matches
    if only_discrepancies and result.annotation_matches == result.asr_matches:
      continue
    html_output += "<tr>"
    html_output += f"<td>{result.user_name} {valid_subject_re.match(result.user_name)}</td>"
    html_output += f"<td>{result.trials_project}</td>"
    html_output += f"<td>{result.trials_trial_number}</td>"
    html_output += f"<td>{result.trials_level_number}</td>"
    # Display ground truth from all_ground_truth dictionary
    ground_truth = all_ground_truth.get((result.trials_project, result.trials_trial_number, result.trials_level_number), ["N/A"])
    html_output += f"<td>{', '.join(ground_truth)}</td>"
    html_output += f"<td>{', '.join(result.asr_words) if result.asr_words else 'N/A'}</td>"
    html_output += f"<td>{result.annotation_matches}</td>"
    html_output += f"<td>{result.asr_matches}</td>"
    # https://www.w3schools.com/charsets/ref_utf_dingbats.asp
    if all(result.audiology_asr_matches):
      html_output += "<td>&#9989;</td>" # a check mark
    else:
      html_output += "<td>&#10008;</td>" # heavy ballot x
    # html_output += f"<td>{result.audiology_asr_matches}</td>"
    audio_url = f"https://quicksin.stanford.edu/uploads/{result.results_reply_filename}.wav"
    html_output += f'<td><audio controls> <source src={audio_url} type=audio/mp4>Your browser does not support the audio element.</audio></td>'
    html_output += "</tr>"
    row_count += 1

  html_output += """
  </table>

  </body>
  </html>
  """
  return html_output, row_count
