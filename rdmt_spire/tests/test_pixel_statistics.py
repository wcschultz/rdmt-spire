import asdf
import numpy as np
from roman_datamodels.dqflags import pixel as dqflags

from ..monitors.pixel_statistics import PixelStatisticsMonitor


class _FakeWCS:
    """
    Minimal stand-in for a gwcs.WCS pixel->sky transform. Implements a
    simple linear tangent-plane-like mapping so wcs(x, y) returns
    (ra, dec) in degrees with an approximately constant plate scale,
    just enough for testing PixelStatisticsMonitor without a real WCS.
    """

    def __init__(self, crval=(10.0, 20.0), plate_scale_arcsec=0.11, nx=4088, ny=4088):
        self.ra0, self.dec0 = crval
        self.scale_deg = plate_scale_arcsec / 3600.0
        self.x0 = (nx - 1) / 2.0
        self.y0 = (ny - 1) / 2.0
        self.cosdec0 = np.cos(np.deg2rad(self.dec0))

    def __call__(self, x, y):
        dx = x - self.x0
        dy = y - self.y0
        ra = self.ra0 + (dx * self.scale_deg) / self.cosdec0
        dec = self.dec0 + dy * self.scale_deg
        return ra, dec


def _build_fake_l2_tree(nx=4088, ny=4088, plate_scale_arcsec=0.11, seed=0):
    """
    Build a fake Roman L2 ASDF file with enough structure for PixelStatisticsMonitor to run.

    Returns
    -------
    fake_asdf : asdf.AsdfFile
        In-memory AsdfFile with tree["roman"]["meta"]["wcs"],
        tree["roman"]["data"], and tree["roman"]["dq"] populated.
    """
    rng = np.random.default_rng(seed)

    # Fake science data: DN/s, baseline + noise
    data = rng.normal(loc=1.0, scale=0.1, size=(ny, nx)).astype(np.float32)

    # Fake DQ array, all good by default
    dq = np.zeros((ny, nx), dtype=np.uint32)

    # Flag a few pixels so saturation/masking metrics aren't trivially zero
    dq[0, 0] |= dqflags["SATURATED"]
    dq[1, 1] |= dqflags["SATURATED"] | dqflags["DO_NOT_USE"]
    dq[2, 2] |= dqflags["DO_NOT_USE"]

    wcs = _FakeWCS(plate_scale_arcsec=plate_scale_arcsec, nx=nx, ny=ny)

    tree = {
        "roman": {
            "meta": {
                "wcs": wcs,
            },
            "data": data,
            "dq": dq,
        }
    }

    return asdf.AsdfFile(tree)

def test_pixel_statistics_valid_input():
    """
    White-noise sanity check:
    For pure white noise, the low-frequency and high-frequency power
    should be comparable, giving a power ratio near 1.
    """
    fake_tree = _build_fake_l2_tree()

    monitor = PixelStatisticsMonitor(
        fake_tree,
        verbose=False,
    )
    monitor.run()

    data_cards = monitor.get_data_card('all')

    assert len(data_cards) == 23

    # Checking plate scale calculations
    ps_data_card = monitor.get_data_card("PLATE_SCALE_CENTER_X")

    assert ps_data_card.data_name.upper() == "PLATE_SCALE_CENTER_X"
    assert ps_data_card.data_unit == "arcsec/pixel"
    assert ps_data_card.evaluation_value is not None
    assert np.isfinite(ps_data_card.data_value)

    # Checking delta plate scale calculations
    delta_ps_data_card = monitor.get_data_card("DELTA_PLATE_SCALE_CORNER_BL")
    
    assert delta_ps_data_card.data_name.upper() == "DELTA_PLATE_SCALE_CORNER_BL"
    assert delta_ps_data_card.data_unit == "arcsec/pixel"
    assert delta_ps_data_card.evaluation_value is not None
    assert np.isfinite(delta_ps_data_card.data_value)

    # Checking ramp value calculations
    ramp_val_data_card = monitor.get_data_card("MIN_RAMP_VALUE")
        
    assert ramp_val_data_card.data_name.upper() == "MIN_RAMP_VALUE"
    assert ramp_val_data_card.data_unit == "DN/s"
    assert ramp_val_data_card.evaluation_value is not None
    assert np.isfinite(ramp_val_data_card.data_value)

    # Checking number of saturated pixels
    nsat_data_card = monitor.get_data_card("N_SATURATED_PIX")
            
    assert nsat_data_card.data_name.upper() == "N_SATURATED_PIX"
    assert nsat_data_card.data_unit == "pixels"
    assert nsat_data_card.evaluation_value is not None
    assert np.isfinite(nsat_data_card.data_value)
    assert nsat_data_card.data_value == 2
