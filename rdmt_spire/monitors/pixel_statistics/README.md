# Pixel Statistics Monitor

This monitor evaluates the health of a Roman WFI Level 2 (L2) science image by calculating the plate scale at multiple areas of the detector (using the WCS information in the L2 meta) as well as various ramp-value statistics from the science image. It summarizes whether the local plate scale at key detector locations is within expected bounds, whether the plate scale is locally isotropic (equal in X and Y), and how saturated pixel counts and ramp DN/s values behave across the image.

The monitor writes a set of metrics into the output datacards and then evaluates a subset of them against thresholds defined in `pixel_statistics_constants.py`.

## Metrics Computed

### Plate Scale

The plate scale is calculated using the WCS information at five fixed points of the detector: the Bottom Left (BL), Bottom Right (BR), Top Left (TL), Top Right (TR), and the center.

- **PLATE_SCALE_CENTER_X / _Y**: Local plate scale at the detector center, in arcsec/pixel.

- **PLATE_SCALE_CORNER_BL/BR/TL/TR_X / _Y**: Local plate scale at each of the four corners, in arcsec/pixel.

- **DELTA_PLATE_SCALE_CENTER**: Difference between X and Y plate scale at the center (`scale_x` − `scale_y`), in arcsec/pixel.

- **DELTA_PLATE_SCALE_CORNER_BL/BR/TL/TR**: Difference between X and Y plate scale at each corner (`scale_x` − `scale_y`), in arcsec/pixel.


### Ramp Values

Computed on the science data array with `SATURATED` and `DO_NOT_USE` pixels masked out.

- **N_SATURATED_PIX**: Count of pixels flagged as saturated (counted independently of the `DO_NOT_USE` mask).

- **MIN_RAMP_VALUE** / **MAX_RAMP_VALUE**: Minimum and maximum pixel value in the masked image, in DN/s.

- **MEAN_RAMP_VALUE** / **MEDIAN_RAMP_VALUE**: Mean and median pixel value in the masked image, in DN/s.

- **STD_RAMP_VALUE**: Standard deviation of pixel values in the masked image, in DN/s.

- **P95_RAMP_VALUE** / **P05_RAMP_VALUE**: 95th and 5th percentile pixel values in the masked image, in DN/s.

## Evaluation Rules

The monitor stores a pass/fail evaluation for each metric. Only a subset of computed metrics have defined thresholds; the rest are marked as passing automatically and are tracked for trending only.

- **PLATE_SCALE_CENTER_X** passes when it is greater than or equal to `PLATE_SCALE_CENTER_X_THRESHOLD`.

- **PLATE_SCALE_CENTER_Y** passes when it is greater than or equal to `PLATE_SCALE_CENTER_Y_THRESHOLD`.

- **DELTA_PLATE_SCALE_CENTER** passes when it is less than or equal to `DELTA_PLATE_SCALE_CENTER_THRESHOLD`.

- **DELTA_PLATE_SCALE_CORNER_BL** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_BL_THRESHOLD`.

- **DELTA_PLATE_SCALE_CORNER_BR** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_BR_THRESHOLD`.

- **DELTA_PLATE_SCALE_CORNER_TL** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_TL_THRESHOLD`.

- **DELTA_PLATE_SCALE_CORNER_TR** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_TR_THRESHOLD`.

All other metrics (plate scale at the four corners individually, and all ramp value metrics) are not evaluated against a threshold and always pass. This is so they can be tracked for trending. 