from audio import AudioDB, AudioOutputBP
from utils import relpath

class QuickSpec:
    trials_table = "quick_trials"
    results_table = "quick_results"
    asr_table = "quick_asr"
    annotations_table = "quick_annotations"
    audio_files = relpath("all_spin_index.csv")

class QuickDB(QuickSpec, AudioDB):
    csv_keys = (
        "active", "lang", "trial_number", "level_number", "snr", "filename",
        "answer")

    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class QuickOutputBP(QuickSpec, AudioOutputBP):
    audio_keys = (
        "id", "snr", "lang", "level_number", "trial_number", "filename",
        "answer")
    audio_done = [1, 0, "--", 0, 1, "", 1]

    def __init__(self, db, name="quick", url_prefix="/quick"):
        super().__init__(db, name, url_prefix)

