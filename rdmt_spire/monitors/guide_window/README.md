# Guide Window Monitor

This monitor evaluates Roman FGS guide-window performance from the tracking products in an ASDF file. It summarizes whether guide-star acquisition succeeded, whether the window is saturated, how stable the background and noise are, whether the observed count rate matches the predicted guide-star brightness, and whether the centroid behavior is consistent with expectations.

The monitor writes a set of metrics into the output datacards and then evaluates each metric against thresholds defined in `rdmt_spire/constants/guide_window_constants.py`.

## Metrics Computed
### Acquisition and saturation
- **acquisition_status**: String status describing whether guide-star acquisition succeeded.
- **saturation_status**: String status describing whether the guide window is saturated.

### Background and noise
- **median_background**: Median background level across tracking frames, in DN.
- **mean_noise**: Mean background standard deviation across tracking frames, in DN.
- **median_background_std**: Standard deviation of the per-frame background medians, in DN.
- **noise_std**: Standard deviation of the per-frame noise estimates (background standard deviation across tracking frames), in DN.
- **num_background_outliers**: Number of frames whose background median is more than 3 standard deviations above the mean background median.
- **num_noise_outliers**: Number of frames whose noise estimate is more than 3 standard deviations above the mean noise estimate.

### Count-rate behavior
- **mean_count_rate**: Mean observed guide-star count rate across frames, in DN/s.
- **std_count_rate**: Standard deviation of the observed count rate across frames, in DN/s.
- **num_count_rate_outliers**: Number of frames whose count rate is more than 3 standard deviations above the mean count rate.

### Centroid behavior
These metrics are only calculated when acquisition succeeds.
- **rms_centroid_error**: RMS radial scatter of the tracking centroids about their mean position, in pixels.
- **rms_centroid_offset**: Radial offset between the mean measured centroid position and the predicted guide-star position, in pixels.

## Evaluation Rules

The monitor stores a pass/fail evaluation for each metric. A metric passes when it stays within the corresponding threshold and fails otherwise.

- **acquisition_status** passes only when the status is `SUCCESS`.
- **saturation_status** passes only when the status is `not_saturated`.
- **median_background** passes when it is less than or equal to `MEDIAN_BACKGROUND_THRESHOLD`.
- **mean_noise** passes when it is less than or equal to `MEAN_NOISE_THRESHOLD`.
- **median_background_std** passes when it is less than or equal to `BACKGROUND_STD_THRESHOLD`.
- **noise_std** passes when it is less than or equal to `NOISE_STD_THRESHOLD`.
- **num_background_outliers** passes when it is less than or equal to `NUM_BACKGROUND_OUTLIERS_THRESHOLD`.
- **num_noise_outliers** passes when it is less than or equal to `NUM_NOISE_OUTLIERS_THRESHOLD`.
- **mean_count_rate** passes when it lies within `COUNT_RATE_MATCHING_FACTOR` standard deviations of the predicted count rate.
- **std_count_rate** passes when the observed scatter is smaller than the distance from the predicted count rate to the predicted bright and faint count-rate limits, after applying `FGS_LIMIT_MATCHING_FACTOR`.
- **num_count_rate_outliers** passes when it is less than or equal to `NUM_COUNT_RATE_OUTLIERS_THRESHOLD`.
- **rms_centroid_error** passes only when acquisition succeeded and the RMS centroid scatter is below the optical-element-specific threshold:
  - `WIM_RMS_JITTER_THRESHOLD` for WIM modes
  - `PRISM_RMS_JITTER_THRESHOLD` for prism modes
  - `GRISM_RMS_JITTER_THRESHOLD` for grism modes
  - `DEF_RMS_JITTER_THRESHOLD` for defocused modes
- **rms_centroid_offset** passes only when acquisition succeeded and the offset is less than or equal to `RMS_CENTROID_OFFSET_THRESHOLD`.
