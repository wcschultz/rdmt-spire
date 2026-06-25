# 1/f Noise Monitor

This monitor computes a power ratio that compares low-frequency power (below `cutoff_freq`) to high-frequency "white noise" power (above `cutoff_freq`). A lower ratio indicates a more successful [1/f](https://roman-docs.stsci.edu/roman-instruments/the-wide-field-instrument/wfi-detectors/instrumental-noise#InstrumentalNoise-1/fNoiseOneOverFNoise) noise removal. The monitor can be run to calculate the power ratio of a single amplifier, but the default that is stored in the `Reef` table is the average of all amplifiers.

The metrics computed by the monitor are:
- **noise_1f_power_ratio**: The ratio of low-frequency power to high-frequency power

## Running the Monitor
With an open ASDF file, the monitor can be run as follows:
```python
from rdmt_spire.monitors.noise_1f import Noise1fMonitor

monitor = Noise1fMonitor(
        asdf_file_tree,
        amp="all",
        cutoff_freq=1100,
        verbose=False
        )

# Calculate metrics and evaluate the 1/f noise removal
monitor.run()
```

The computed power ratio metric can be then obtained by the following:
```python
power_ratio = monitor.get_data("noise_1f_power_ratio")
```

And the name, unit, and evaluation boolean (i.e., whether the image passed or failed the monitor evaluation) can be obtained by the following:
```python
# Define the data card
data_card = monitor.get_data_card("noise_1f_power_ratio")

# Return the name of the metric (noise_1f_power_ratio)
data_card.data_name

# Returns the unit of the metric ('' since it's a unitless quantity)
data_card.data_unit

# Returns the evaluation boolean (True if noise_1f_power_ratio < threshold)
data_card.evaluation_value 
```
## Implementation Details

The only required input to the monitor is the [Level-2 (L2) science file](https://roman-docs.stsci.edu/data-handbook/wfi-data-levels-and-products#WFIDataLevelsandProducts-Level2). The image goes through the following steps: 

1) For each of the amplifiers, a subarray of the image is extracted that corresponds to the given amplifier's pixels. 
2) The array is transformed to a time-series ordered pixel stream. 
3) The array is sigma-clipped to remove outlier pixels, and these clipped pixel values are replaced with the mean of the clipped distribution. 
4) The power spectrum of the time-ordered pixel stream is computed using a [Fast Fourier Transform (FFT)](https://en.wikipedia.org/wiki/Fast_Fourier_transform). Because the input signal is real, the Fourier transform is symmetric, so only the non-negative frequency components ("one-sided" spectrum) are retained. 
5) The spectrum is then split at the specified cutoff frequency into low-frequency (1/f-dominated) and high-frequency (white-noise-dominated) regions, which are used to compute the mean power in each band.
6) The power ratio is then defined as the ratio of the mean low-frequency power to the mean high-frequency (white noise) power.

If the specified amplifer is `"all"`, then the power ratio value that is evaluated is the mean of all amps' power ratios. If the 1/f power ratio metric is less than the power ratio threshold (currently in `rdmt_spire/constants/noise_1f_constants.py`), then the Reference Pixel correction is considered successful.

---

_For more information on how 1/f noise is characterized and how the IRRC is applied to Roman data products, see the tech report, [Roman-STScI-000673](https://www.stsci.edu/files/live/sites/www/files/home/roman/documentation/technical-documentation/_documents/Roman-STScI-000673.pdf)._