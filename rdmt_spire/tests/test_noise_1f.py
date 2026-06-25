import asdf
import numpy as np

from ..monitors.noise_1f import Noise1fMonitor


def test_noise_1f_white_noise_ratio_near_unity():
    """
    White-noise sanity check:
    For pure white noise, the low-frequency and high-frequency power
    should be comparable, giving a power ratio near 1.
    """
    rng = np.random.default_rng(12345)

    # Create fake white-noise image
    white_noise = rng.normal(loc=0.0, scale=1.0, size=(4088, 4088))

    fake = asdf.AsdfFile()
    fake.tree["roman"] = {"data": white_noise}

    monitor = Noise1fMonitor(
        fake,
        amp="all",
        cutoff_freq=1100,
        verbose=False,
    )
    monitor.run()

    data_cards = monitor.get_data_card('all')

    assert len(data_cards) == 1

    assert data_cards[0].data_name == 'noise_1f_power_ratio'
    assert data_cards[0].data_unit == ''
    assert data_cards[0].evaluation_value is not None 

    power_ratio = monitor.get_data("noise_1f_power_ratio")

    assert np.isfinite(power_ratio)
    assert 0.9 < power_ratio < 1.1
