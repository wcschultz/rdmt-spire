import asdf
import numpy as np
import pytest

from ..monitors.guide_window import GuideWindowMonitor


def _build_monitor(
    *,
    num_frames=300,
    image_shape=(16, 16),
    optical_element="F062",
    fgs_mode="WIM_TRK",
    wsm_edge='red',
    centroid_quality="CQ_GOOD",
    include_centroids=True,
):
    """Create a GuideWindowMonitor with a synthetic but valid ASDF tree."""
    if "WIM" in fgs_mode:
        image_shape = (16, 16)
    elif "WSM" in fgs_mode:
        image_shape = (32, 16) # TODO: Check if the implementation is actually handling these dimensions correctly. The ones here match the data...

    rows, cols = image_shape
    signal = np.zeros((num_frames, rows, cols), dtype=float)
    pedestal = np.zeros_like(signal)

    # Add a bright source that drifts slightly to create frame-to-frame variation.
    if "WIM" in fgs_mode:
        r = rows // 2
        c = cols // 2
    elif "WSM" in fgs_mode:
        if optical_element.lower() == 'prism':
            r = rows // 8 if wsm_edge == 'blue' else 7 * rows // 8
        else:
            r = rows // 8 if wsm_edge == 'red' else 7 * rows // 8
        c = cols // 2
    for i in range(num_frames):
        signal[i, r, c] = 1000 + 10*(i % 10)

    centroid_tree = {}
    if include_centroids:
        base = np.array([cols / 2.0, rows / 2.0])
        jitter = np.tile(np.array([0.05, -0.03]), (num_frames, 1))
        centroid_tree = {
            "track_centroids": base + jitter,
            "track_centroid_quality": np.array([centroid_quality] * num_frames),
        }

    af = asdf.AsdfFile()
    af.tree["roman"] = {
        "track_data": {
            "signal_resultants": signal,
            "pedestal_resultants": pedestal,
        },
        "centroid": centroid_tree,
        "meta": {
            "fgs_modes_used": [fgs_mode],
            "wsm_edge_used": wsm_edge,
            "track_signal_resultant_exp_time": 2.0,
            "track_pedestal_resultant_exp_time": 1.0,
            "instrument": {"optical_element": optical_element},
            "guide_star": {
                "predicted_x": cols / 2.0,
                "predicted_y": rows / 2.0,
                "predicted_count_rate": 10.0,
                "predicted_fgs_mag": 15.0,
                "predicted_fgs_faint_mag": 16.0,
                "predicted_fgs_bright_mag": 14.0,
            },
        },
    }
    return GuideWindowMonitor(af)


def test_process_centroids_returns_expected_shapes():
    monitor = _build_monitor(num_frames=300)

    mean_centroid_positions, rms_x_centroid_error, rms_y_centroid_error = monitor._process_centroids()

    assert mean_centroid_positions.shape == (2,)
    assert np.isfinite(rms_x_centroid_error)
    assert rms_x_centroid_error >= 0
    assert np.isfinite(rms_y_centroid_error)
    assert rms_y_centroid_error >= 0


def test_annulus_mask_vs_count_rate_mask():
    configs = [
        {"fgs_mode": "WIM_TRK"},
        {"fgs_mode": "WSM_TRK", "optical_element": "prism", "wsm_edge": "red"},
        {"fgs_mode": "WSM_TRK", "optical_element": "prism", "wsm_edge": "blue"},
        {"fgs_mode": "WSM_TRK", "optical_element": "grism", "wsm_edge": "red"},
        {"fgs_mode": "WSM_TRK", "optical_element": "grism", "wsm_edge": "blue"},
    ]

    for config in configs:
        monitor = _build_monitor(num_frames=5, **config)
    
        arr = monitor.asdf_file.tree["roman"]["track_data"]["signal_resultants"]
        if "WIM" in config["fgs_mode"]:
            background_mask = monitor._get_wim_annulus_mask(arr, edge_buffer=2, annulus_width=2)
            count_rate_mask = monitor._create_wim_brightest_pixel_masks(arr)[0]
        else:
            background_mask = monitor._get_wsm_annulus_mask(arr, edge_buffer=2, annulus_width=2)
            count_rate_mask = monitor._create_wsm_brightest_pixel_masks(arr)[0]

        assert background_mask.shape == arr.shape[1:]
        assert count_rate_mask.shape == arr.shape[1:]
        assert np.sum(count_rate_mask * background_mask) == 0  # Masks should not overlap

@pytest.mark.parametrize(
    "signal,saturation_threshold,expected",
    [
        (np.full((10, 4, 4), 70000.0), 65535, "SATURATED"),
        (
            np.concatenate(
                [np.full((2, 4, 4), 70000.0), np.full((8, 4, 4), 100.0)],
                axis=0,
            ),
            65535,
            "SOMETIMES_SATURATED",
        ),
        (np.full((10, 4, 4), 100.0), 65535, "NOT_SATURATED"),
    ],
)
def test_check_saturation_states(signal, saturation_threshold, expected):
    monitor = _build_monitor(num_frames=signal.shape[0])
    monitor.asdf_file.tree["roman"]["track_data"]["signal_resultants"] = signal

    result = monitor.check_saturation(saturation_threshold=saturation_threshold)

    assert result == expected


def test_check_acquisition_status_missing_centroids():
    monitor = _build_monitor(include_centroids=False)

    success, acquisition_status = monitor.check_acquisition_status()

    assert success is False
    assert acquisition_status == "NO_TRACK_CENTROIDS"


def test_check_acquisition_status_too_few_centroids():
    monitor = _build_monitor(num_frames=20)

    success, acquisition_status = monitor.check_acquisition_status()

    assert success is False
    assert acquisition_status == "TOO_FEW_CENTROIDS"


def test_check_acquisition_status_bad_centroid_quality():
    monitor = _build_monitor(centroid_quality="CQ_BAD_FIT")

    success, acquisition_status = monitor.check_acquisition_status()

    assert success is False
    assert acquisition_status == "CQ_BAD_FIT"


def test_calculate_count_rates_returns_finite_metrics():
    configs = [
        {"fgs_mode": "WIM_TRK"},
        {"fgs_mode": "WSM_TRK", "optical_element": "prism", "wsm_edge": "red"},
        {"fgs_mode": "WSM_TRK", "optical_element": "prism", "wsm_edge": "blue"},
        {"fgs_mode": "WSM_TRK", "optical_element": "grism", "wsm_edge": "red"},
        {"fgs_mode": "WSM_TRK", "optical_element": "grism", "wsm_edge": "blue"},
    ]

    for config in configs:

        monitor = _build_monitor(num_frames=30, **config)

        mean_count_rate, std_count_rate, num_count_rate_outliers = monitor.calculate_count_rates()

        assert np.isfinite(mean_count_rate)
        assert np.isfinite(std_count_rate)
        assert mean_count_rate > 0
        assert std_count_rate > 0
        assert num_count_rate_outliers >= 0


def test_run_populates_expected_datacards_and_evaluations():
    monitor = _build_monitor(num_frames=300)

    monitor.run()

    cards = monitor.get_data_card("all")
    card_names = {card.data_name for card in cards}

    expected_metrics = {
        "acquisition_status",
        "saturation_status",
        "median_background",
        "mean_noise",
        "median_background_std",
        "noise_std",
        "num_background_outliers",
        "num_noise_outliers",
        "mean_count_rate",
        "std_count_rate",
        "num_count_rate_outliers",
        "rms_x_centroid_error",
        "rms_y_centroid_error",
        "rms_centroid_offset",
    }

    assert expected_metrics.issubset(card_names)
    assert isinstance(monitor.get_data_card("acquisition_status").evaluation_value, bool)
    assert isinstance(monitor.get_data_card("saturation_status").evaluation_value, bool)
