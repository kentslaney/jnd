from audio import AudioDB, AudioOutputBP
from storage import relpath

class AudioSpec:
    trials_table = "audio_trials"
    results_table = "audio_results"
    asr_table = "audio_asr"
    annotations_table = "audio_annotations"

class QuickSpec(AudioSpec):
    audio_files = relpath("metadata/all_spin_index.csv")
    project_key = "quick"

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

class Qs3Spec(AudioSpec):
    audio_files = relpath("metadata/QS3dB_transcript.csv")
    project_key = "qs3"

class Qs3DB(Qs3Spec, AudioDB):
    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class Qs3BP(Qs3Spec, AudioOutputBP):
    def __init__(self, db, name="qs3", url_prefix="/qs3"):
        super().__init__(db, name, url_prefix)

class Nu6Spec(AudioSpec):
    audio_files = relpath("metadata/NU6_transcript.csv")
    project_key = "nu6"

class Nu6DB(Nu6Spec, AudioDB):
    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class Nu6BP(Nu6Spec, AudioOutputBP):
    def __init__(self, db, name="nu6", url_prefix="/nu6"):
        super().__init__(db, name, url_prefix)

class AzBioSpec(AudioSpec):
    audio_files = relpath("metadata/AzBio_transcript.csv")
    project_key = "azbio"

class AzBioDB(AzBioSpec, AudioDB):
    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class AzBioBP(AzBioSpec, AudioOutputBP):
    def __init__(self, db, name="azbio", url_prefix="/azbio"):
        super().__init__(db, name, url_prefix)

class CncSpec(AudioSpec):
    audio_files = relpath("metadata/CNC_transcript.csv")
    project_key = "cnc"

class CncDB(CncSpec, AudioDB):
    def db_init_hook(self):
        super().db_init_hook()
        self.parse_csv(__class__)

class CncBP(CncSpec, AudioOutputBP):
    def __init__(self, db, name="cnc", url_prefix="/cnc"):
        super().__init__(db, name, url_prefix)
