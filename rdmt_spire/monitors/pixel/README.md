# Pixel Monitor

This monitor evaluates the health of a Roman WFI Level 2 (L2) science image by calculating the plate scale at multiple areas of the detector (using the WCS information in the L2 meta) as well as various ramp-value statistics from the science image. It summarizes whether the local plate scale at key detector locations is within expected bounds, whether the plate scale is locally isotropic (equal in X and Y), and how saturated pixel counts and ramp DN/s values behave across the image.

The monitor writes a set of metrics into the output datacards and then evaluates a subset of them against thresholds defined in `pixel_statistics_constants.py`.

## Metrics Computed

### Plate Scale

The plate scale is calculated using the WCS information at five fixed points of the detector: the Bottom Left (BL), Bottom Right (BR), Top Left (TL), Top Right (TR), and the center.

- **plate_scale_center_x / _y**: Local plate scale at the detector center, in arcsec/pixel.

- **plate_scale_corner_bl/br/tl/tr_x / _y**: Local plate scale at each of the four corners, in arcsec/pixel.

- **delta_plate_scale_center**: Difference between X and Y plate scale at the center (`scale_x` − `scale_y`), in arcsec/pixel.

- **delta_plate_scale_corner_bl/br/tl/tr**: Difference between X and Y plate scale at each corner (`scale_x` − `scale_y`), in arcsec/pixel.


### Ramp Values

Computed on the science data array with `SATURATED` and `DO_NOT_USE` pixels masked out.

- **n_saturated_pix**: Count of pixels flagged as saturated (counted independently of the `DO_NOT_USE` mask).

- **min_ramp_value** / **max_ramp_value**: Minimum and maximum pixel value in the masked image, in DN/s.

- **mean_ramp_value** / **median_ramp_value**: Mean and median pixel value in the masked image, in DN/s.

- **std_ramp_value**: Standard deviation of pixel values in the masked image, in DN/s.

- **p95_ramp_value** / **p05_ramp_value**: 95th and 5th percentile pixel values in the masked image, in DN/s.

## Evaluation Rules

The monitor stores a pass/fail evaluation for each metric. Only a subset of computed metrics have defined thresholds; the rest are marked as passing automatically and are tracked for trending only.

- **plate_scale_center_x** passes when it is greater than or equal to `PLATE_SCALE_CENTER_X_THRESHOLD`.

- **plate_scale_center_y** passes when it is greater than or equal to `PLATE_SCALE_CENTER_Y_THRESHOLD`.

- **delta_plate_scale_center** passes when it is less than or equal to `DELTA_PLATE_SCALE_CENTER_THRESHOLD`.

- **delta_plate_scale_corner_bl** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_BL_THRESHOLD`.

- **delta_plate_scale_corner_br** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_BR_THRESHOLD`.

- **delta_plate_scale_corner_tl** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_TL_THRESHOLD`.

- **delta_plate_scale_corner_tr** passes when it is less than or equal to `DELTA_PLATE_SCALE_CORNER_TR_THRESHOLD`.

All other metrics (plate scale at the four corners individually, and all ramp value metrics) are not evaluated against a threshold and always pass. This is so they can be tracked for trending. 