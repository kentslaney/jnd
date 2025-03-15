from audio import AudioDB, AudioOutputBP
from utils import relpath

class QuickSpec:
    trials_table = "quick_trials"
    results_table = "quick_results"
    asr_table = "quick_asr"
    annotations_table = "quick_annotations"
    audio_files = relpath("metadata/all_spin_index.csv")

class QuickDB(QuickSpec, AudioDB):
    csv_keys = (
        "active", "lang", "trial_number", "level_number", "snr", "filename",
        "answer")

    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class QuickBP(QuickSpec, AudioOutputBP):
    audio_keys = (
        "id", "snr", "lang", "level_number", "trial_number", "filename",
        "answer")
    audio_done = [1, 0, "--", 0, 1, "", 1]

    def __init__(self, db, name="quick", url_prefix="/quick"):
        super().__init__(db, name, url_prefix)

class Nu6Spec:
    trials_table = "nu6_trials"
    results_table = "nu6_results"
    asr_table = "nu6_asr"
    annotations_table = "nu6_annotations"
    audio_files = relpath("metadata/NU6_transcript.csv")

class Nu6DB(Nu6Spec, AudioDB):
    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class Nu6BP(Nu6Spec, AudioOutputBP):
    def __init__(self, db, name="nu6", url_prefix="/nu6"):
        super().__init__(db, name, url_prefix)

class AzBioSpec:
    trials_table = "azbio_trials"
    results_table = "azbio_results"
    asr_table = "azbio_asr"
    annotations_table = "azbio_annotations"
    audio_files = relpath("metadata/AzBio_transcript.csv")

class AzBioDB(AzBioSpec, AudioDB):
    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class AzBioBP(AzBioSpec, AudioOutputBP):
    def __init__(self, db, name="azbio", url_prefix="/azbio"):
        super().__init__(db, name, url_prefix)

class CncSpec:
    trials_table = "cnc_trials"
    results_table = "cnc_results"
    asr_table = "cnc_asr"
    annotations_table = "cnc_annotations"
    audio_files = relpath("metadata/CNC_transcript.csv")

class CncDB(CncSpec, AudioDB):
    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class CncBP(CncSpec, AudioOutputBP):
    def __init__(self, db, name="cnc", url_prefix="/cnc"):
        super().__init__(db, name, url_prefix)
