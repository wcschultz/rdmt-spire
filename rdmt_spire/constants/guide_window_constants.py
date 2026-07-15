# guide window size specifications
WIM_TRACK_SIZE = 16
WSM_TRACK_X_SIZE = 16
WSM_TRACK_Y_SIZE = 32

WSM_GW_TOP = "TOP"
WSM_GW_BOTTOM = "BOTTOM"

WSM_EDGE_LOCATIONS = {
    ("PRISM", "RED"): WSM_GW_TOP,
    ("PRISM", "BLUE"): WSM_GW_BOTTOM,
    ("GRISM", "RED"): WSM_GW_BOTTOM,
    ("GRISM", "BLUE"): WSM_GW_TOP,
}

# thresholds for evaluating the metrics
MEDIAN_BACKGROUND_THRESHOLD = 1000 # DN
MEAN_NOISE_THRESHOLD = 100 # DN
BACKGROUND_STD_THRESHOLD = 100 # DN
NOISE_STD_THRESHOLD = 10 # DN
NUM_BACKGROUND_OUTLIERS_THRESHOLD = 0
NUM_NOISE_OUTLIERS_THRESHOLD = 0
COUNT_RATE_MATCHING_FACTOR = 3 # number of standard deviations that the mean count rate can deviate from the predicted count rate before it is marked as failed
FGS_LIMIT_MATCHING_FACTOR = 3 # number of standard deviations to compare with the predicted limits. If limits are closer to the predicted count rate, it is marked as failed.
NUM_COUNT_RATE_OUTLIERS_THRESHOLD = 0
RMS_CENTROID_OFFSET_THRESHOLD = 2 # pixels (~220 mas)

# Specify the RMS jitter requirements for each mode. 
# These are used to determine if the jitter is within acceptable limits for each mode.
WIM_RMS_JITTER_REQUIREMENT = 0.1 # pixels (~11 mas)
PRISM_RMS_JITTER_REQUIREMENT = 0.4 # pixels (~44 mas)
GRISM_RMS_JITTER_REQUIREMENT = 0.9 # pixels (~99 mas)
DEF_RMS_JITTER_REQUIREMENT = 0.5 # pixels (~55 mas)

# TODO: Update the RMS jitter thresholds once we have on-sky performance from commissioning.
# The current values are based on pre-launch requirements.
RMS_X_JITTER_THRESHOLDS = {
    "WIM": WIM_RMS_JITTER_REQUIREMENT,
    "PRISM": PRISM_RMS_JITTER_REQUIREMENT,
    "GRISM": GRISM_RMS_JITTER_REQUIREMENT,
    "DEFOCUS": DEF_RMS_JITTER_REQUIREMENT,
}

RMS_Y_JITTER_THRESHOLDS = {
    "WIM": WIM_RMS_JITTER_REQUIREMENT,
    "PRISM": PRISM_RMS_JITTER_REQUIREMENT,
    "GRISM": GRISM_RMS_JITTER_REQUIREMENT,
    "DEFOCUS": DEF_RMS_JITTER_REQUIREMENT,
}

