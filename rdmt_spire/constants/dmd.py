from enum import StrEnum


class FileTypes(StrEnum):
    L2_SCIENCE = "science_wfi_level_2"
    L1_GUIDE_WINDOW = "guide_window_wfi_level_1"
    L4_DET_SOURCES = "science_wfi_level_4" #TODO: check what this will actually be

class ReprocessingStates(StrEnum):
    PROMPT = "none"
    REPROCESSED = "reprocessed"
    DATA_RELEASE = "data_release"