import logging

import asdf
import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from roman_datamodels.dqflags import pixel as dqflags

from ...constants.pixel_statistics_constants import (
    DELTA_PLATE_SCALE_CENTER_THRESHOLD,
    DELTA_PLATE_SCALE_CORNER_BL_THRESHOLD,
    DELTA_PLATE_SCALE_CORNER_BR_THRESHOLD,
    DELTA_PLATE_SCALE_CORNER_TL_THRESHOLD,
    DELTA_PLATE_SCALE_CORNER_TR_THRESHOLD,
    PIXEL_STATISTICS_METRIC_NAMES,
    PLATE_SCALE_CENTER_X_THRESHOLD,
    PLATE_SCALE_CENTER_Y_THRESHOLD,
)
from ..monitor_base import BaseMonitor

logger = logging.getLogger(__name__)

class PixelStatisticsMonitor(BaseMonitor):
    """
    Monitor for evaluating pixel statistics from Roman L2 science data.

    Parameters
    ----------
    asdf_file : asdf.AsdfFile
        Open ASDF file containing the Roman L2 data and metadata.
    verbose : bool, optional
        If ``True``, enable additional runtime verbosity.
    """
    def __init__(self,
                 asdf_file: asdf.AsdfFile,
                 verbose=False):
        """
        Initialize the PixelStatisticsMonitor monitor.

        Parameters
        ----------
        asdf_file : asdf.AsdfFile
            Open ASDF file containing a Roman WFI L2 image in
            asdf_file.tree["roman"]["data"]
        verbose : bool, optional
            If True, print logging during processing.
        """
        super().__init__(asdf_file)

        self.monitor_name = 'pixel_statistics'
        self.log.append(f"{self.monitor_name}: initialized")

        self.verbose = verbose


    def calculate_metrics(self):
        """
        Compute and store pixel statistics monitoring metrics.
        """
        # Merged dict with plate scale + ramp stats stored
        metrics_dict = self.calculate_plate_scales() | self.calculate_ramp_values()

        for metric, val in metrics_dict.items():
            if "PLATE_SCALE" in metric:
                unit = "arcsec/pixel"

            elif "RAMP_VALUE" in metric:
                unit = "DN/s"

            else:
                unit = "pixels"

            self.append_data(metric, val, unit)


    def evaluate_metrics(self):
        """
        Evaluate computed metrics against monitor acceptance thresholds.
        """
        # Dict of the metrics we actually need to evaluate
        THRESHOLDS = {
            "PLATE_SCALE_CENTER_X": PLATE_SCALE_CENTER_X_THRESHOLD,
            "PLATE_SCALE_CENTER_Y": PLATE_SCALE_CENTER_Y_THRESHOLD,
            "DELTA_PLATE_SCALE_CORNER_BL": DELTA_PLATE_SCALE_CORNER_BL_THRESHOLD,
            "DELTA_PLATE_SCALE_CORNER_BR": DELTA_PLATE_SCALE_CORNER_BR_THRESHOLD,
            "DELTA_PLATE_SCALE_CORNER_TL": DELTA_PLATE_SCALE_CORNER_TL_THRESHOLD,
            "DELTA_PLATE_SCALE_CORNER_TR": DELTA_PLATE_SCALE_CORNER_TR_THRESHOLD,
            "DELTA_PLATE_SCALE_CENTER": DELTA_PLATE_SCALE_CENTER_THRESHOLD,
        }

        for metric_name in PIXEL_STATISTICS_METRIC_NAMES:
            # Only a subset of the metrics are being actually evaluated
            if metric_name in THRESHOLDS:
                if "DELTA" in metric_name:
                    passed = abs(self.get_data(metric_name)) <= THRESHOLDS[metric_name]
                else:
                    passed = self.get_data(metric_name) >= THRESHOLDS[metric_name]

            # If not defined in the constants file, then it's just being set to True to check trending
            else:
                passed = True

            self.add_evaluation(metric_name, passed)


    def calculate_plate_scales(self, step=1.0):
        """
        Calculate the plate scale and X/Y delta for multiple regions of the detector.
        Returns a dict with all plate scale + delta calculations for each of the five regions.
        """
        wcs = self.asdf_file["roman"]["meta"]["wcs"]

        im = self.asdf_file["roman"]["data"]
        im = im.value if hasattr(im, "value") else im
        ny, nx = im.shape

        # Getting the coordinates for the diff regions of the detector
        x_min, x_max = 1, nx - 2
        y_min, y_max = 1, ny - 2
        x_c, y_c = (nx - 1) / 2.0, (ny - 1) / 2.0

        points = {
            "CORNER_BL": (x_min, y_min), # bottom left
            "CORNER_BR": (x_max, y_min), # bottom right
            "CORNER_TL": (x_min, y_max), # top left
            "CORNER_TR": (x_max, y_max), # top right
            "CENTER":    (x_c, y_c),
        }

        results = {}
        for label, (x, y) in points.items():

            sx, sy = self._local_plate_scale(wcs, x, y, step=step)

            results["PLATE_SCALE_" + label + "_X"] = sx
            results["PLATE_SCALE_" + label + "_Y"] = sy

            results["DELTA_PLATE_SCALE_" + label] = sx - sy

        return results


    def calculate_ramp_values(self):
        """
        Calculate different ramp statistics and the number of pixels saturated.
        Returns a dict with metrics.

        Note: Image used in stats calculations have SATURATED and DO_NOT_USE pixels masked.
        """
        im = self.asdf_file["roman"]["data"]
        im = im.value if hasattr(im, "value") else im

        # The DQ array to count n_saturated
        dq = self.asdf_file["roman"]["dq"]

        # Getting mask of saturated pixels
        sat_mask = (dq & dqflags["SATURATED"] != 0)

        # Getting mask of saturated + DNU pixels
        mask = (dq & dqflags["SATURATED"] != 0) & (dq & dqflags["DO_NOT_USE"] != 0)
        masked_im = im[~mask]

        results = {}
        results["N_SATURATED_PIX"] = np.count_nonzero(sat_mask)

        results["MIN_RAMP_VALUE"] = np.min(masked_im)
        results["MAX_RAMP_VALUE"] = np.max(masked_im)

        results["MEAN_RAMP_VALUE"] = np.nanmean(masked_im)
        results["MEDIAN_RAMP_VALUE"] = np.nanmedian(masked_im)
        results["STD_RAMP_VALUE"] = np.nanstd(masked_im)

        results["P95_RAMP_VALUE"] = np.percentile(masked_im, 95)
        results["P05_RAMP_VALUE"] = np.percentile(masked_im, 5)

        return results


    def _local_plate_scale(self, wcs, x, y, step=1.0):
        """
        Local plate scale (arcsec/pixel) in x and y at pixel (x, y),
        using astropy SkyCoord for exact angular separations.

        Parameters
        ----------
        wcs : gwcs.WCS object
            WCS data and metadata, accessed via af.tree["roman"]["meta"]["wcs"].
        x : float
            X coordinate used in plate scale calculation.
        y : float
            Y coordinate used in plate scale calculation.
        steps : float, optional
            The number of pixel steps (left/right/up/down from (x, y)).
            Used to calculate the separation + plate scale.

        Returns
        -------
        scale_x : float
            The plate scale for the x axis of coordinate (x, y)
        scale_y : float
            The plate scale for the y axis of coordinate (x, y)
        """
        # x-direction step
        ra_xp, dec_xp = wcs(x + step, y)
        ra_xm, dec_xm = wcs(x - step, y)

        # Convert step coords to SkyCoords for easier separation calculations
        c_xp = SkyCoord(ra=ra_xp * u.deg, dec=dec_xp * u.deg)
        c_xm = SkyCoord(ra=ra_xm * u.deg, dec=dec_xm * u.deg)

        # Plate scale for x axis
        scale_x = (c_xp.separation(c_xm).to(u.arcsec).value) / (2 * step)

        # y-direction step
        ra_yp, dec_yp = wcs(x, y + step)
        ra_ym, dec_ym = wcs(x, y - step)

        c_yp = SkyCoord(ra=ra_yp * u.deg, dec=dec_yp * u.deg)
        c_ym = SkyCoord(ra=ra_ym * u.deg, dec=dec_ym * u.deg)

        scale_y = (c_yp.separation(c_ym).to(u.arcsec).value) / (2 * step)

        return scale_x, scale_y
