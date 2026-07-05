from rdmt_spire.utilities import aws_utils
import os
import logging
import asdf
import numpy as np
import pandas as pd
from astropy.table import Table
from ..monitor_base import BaseMonitor

logger = logging.getLogger(__name__)

# Get clarity on handling errors. For example, if the filter is not found in the calibration files.
# Should it return an empty dictionary and log the error?
# Also, what is the expected behavior of the monitor if the input file (catalog.parquet) is missing?
# Should it return an empty dictionary and log the error?

class SourceCatalogMonitor(BaseMonitor):
    """
    Source Catalog Monitor derived from class BaseMonitor.
    Reads the source catalog (parquet format) created from an L2 file.
    Bins point sources by brightness and tracks properties:
    sharpness, roundness1, ellipticity, flux_frac_radius_50, flux ratios,
    and flux error ratio.
    """

    def __init__(self, asdf_file: asdf.AsdfFile, datadir: str):
        super().__init__(asdf_file)
        self.monitor_name = "source_catalog"
        self.datadir = datadir
        self.log.append(f"{self.monitor_name}: initialized")

    def _load_data_file(self, filename: str) -> pd.DataFrame:
        """
        Loads a local calibration or parameter file under the data/ directory.
        """        
        path = os.path.join(os.path.dirname(__file__), 'data', filename)
        if filename.endswith('.ecsv'):
            with open(path, 'r') as f:
                content = f.read()
            df = Table.read(content.replace('\t', ' '), format="ascii.ecsv").to_pandas()
        else:
            df = Table.read(path).to_pandas()
        
        # clean up filter column to avoid mismatch caused by different naming conventions in files
        if 'filter' in df.columns:
            df['filter'] = df['filter'].astype(str).str.strip().str.lower()
        return df

    def calculate_metrics(self):
        """
        Calculates source catalog metrics binned by magnitude.
        Adds median, RMS, and NMAD metrics for 8 properties across bright and faint bins.
        """
        # Define properties and statistics for the metrics
        properties = [
            "sharpness",
            "roundness1",
            "ellipticity",
            "flux_frac_radius_50",
            "flux_ratio_aper01_aper02",
            "flux_ratio_aper02_aper04",
            "flux_ratio_aper04_aper08",
            "flux_err_ratio_psf_theory"
        ]
        bins = ["bright", "faint"]
        stats = ["median", "rms", "nmad"]

        # Do we need a  Fallback logic for tests to return dummy values
        # if self.asdf_file.uri is None:

        # Should we use (try,except,raise) clause to log the error
        # except (KeyError, TypeError) as e:
        #    raise RuntimeError(f"SourceCatalogMonitor: failed to retrieve parameter from asdf file: {e}")
        
        # 2. Parse needed values from the ASDF file.
        filename = self.asdf_file["roman"]["meta"]["filename"]
        optical_filter = self.asdf_file["roman"]["meta"]["instrument"]["optical_element"].strip().lower()
        t_exp = self.asdf_file["roman"]["meta"]["exposure"]["exposure_time"]


        # 3. Load calibration parameters
        expected_props = self._load_data_file("expected_photometric_properties.csv")
        zero_points = self._load_data_file("zero_points_20260401.csv")
        filter_params = self._load_data_file("filter_parameters.ecsv")
        thermal_bkg = self._load_data_file("internal_thermal_backgrounds.ecsv")
        zodiacal_light = self._load_data_file("zodiacal_light.ecsv")

        # Lookup parameters helper
        def get_val(df, col, filter_val):
            rows = df[df['filter'] == filter_val]
            if rows.empty:
                raise RuntimeError(f"SourceCatalogMonitor: filter '{filter_val}' not found in parameter table")
            return rows[col].values[0]

        zp = get_val(zero_points, 'Z_R', optical_filter)
        n_eff = get_val(filter_params, 'center_PSF_n_eff_pixel', optical_filter)
        f_peak = get_val(filter_params, 'center_PSF_peak_flux', optical_filter)
        f_thermal = get_val(thermal_bkg, 'rate', optical_filter)
        f_min_zodi = get_val(zodiacal_light, 'rate', optical_filter)

        # Expected values for each property for a given filter
        expected_row = expected_props[expected_props['filter'] == optical_filter]
        if expected_row.empty:
            raise RuntimeError(f"SourceCatalogMonitor: filter '{optical_filter}' not found in expected properties table")
        E_p = {key:expected_row[key].values[0] for key in properties}

        # 4. Construct parquet catalog file path and load it
        file_object=aws_utils.load_file_object(self.datadir, filename.replace('_cal.asdf', '_cat.parquet'))
        df = pd.read_parquet(file_object)

        # 5. Point source selection
        if 'is_extended' not in df.columns:
            raise RuntimeError("SourceCatalogMonitor: 'is_extended' column missing from source catalog")
        df_pts = df[df['is_extended'] == False].copy()

        # 6. Calculate magnitude bin boundaries
        # Saturation mag: m_sat = Zp - 2.5 * log10(alpha_sat)
        # alpha_sat = c_sat / (f_peak * t_exp), where c_sat = 120,000
        c_sat = 120000.0
        alpha_sat = c_sat / (f_peak * t_exp)
        m_sat = zp - 2.5 * np.log10(alpha_sat)

        # Faint limit from SNR = 50 quadratic equation
        snr = 50.0
        snr2 = snr ** 2
        f_bkgd = 2.0 * f_min_zodi + f_thermal

        term_b = snr2 / t_exp
        term_c = (snr2 * n_eff * f_bkgd) / t_exp
        f_source_limit = (term_b + np.sqrt(term_b**2 + 4.0 * term_c)) / 2.0
        m_faint = zp - 2.5 * np.log10(f_source_limit)

        m_mid = (m_sat + m_faint) / 2.0

        self.log.append(f"m_sat: {m_sat:.4f}, m_mid: {m_mid:.4f}, m_faint: {m_faint:.4f}")

        # 7. Subdivide sources
        mab=-2.5*np.log10(df_pts['psf_flux'])+31.4
        cond_bright = (mab > m_sat) & (mab <= m_mid)
        cond_faint = (mab > m_mid) & (mab < m_faint)

        self.append_data("num_sources_bright", np.sum(cond_bright), "")
        self.append_data("num_sources_faint", np.sum(cond_faint), "")

        # 8. Compute property arrays helper
        kappa = 10**((31.4 - zp) / 2.5)

        def compute_properties(df_sub):
            if df_sub.empty:
                return {}

            props = {}
            props["sharpness"] = df_sub["sharpness"].values
            props["roundness1"] = df_sub["roundness1"].values
            props["ellipticity"] = df_sub["ellipticity"].values
            props["flux_frac_radius_50"] = df_sub["fluxfrac_radius_50"].values

            # Division by zero handled by replacing with NaN
            props["flux_ratio_aper01_aper02"] = (df_sub["aper02_flux"] / df_sub["aper01_flux"].replace(0, np.nan)).values
            props["flux_ratio_aper02_aper04"] = (df_sub["aper04_flux"] / df_sub["aper02_flux"].replace(0, np.nan)).values
            props["flux_ratio_aper04_aper08"] = (df_sub["aper08_flux"] / df_sub["aper04_flux"].replace(0, np.nan)).values

            # Theoretical PSF flux error
            f_src = df_sub["psf_flux"].values / kappa
            term_err = t_exp * (n_eff * f_bkgd + f_src)
            # to avoid invalid value error in sqrt
            term_err_clipped = np.clip(term_err, 0.0, None)
            sigma_f = np.sqrt(term_err_clipped) / t_exp
            psf_flux_err_theory = sigma_f * kappa
            # to avoid invalid value error
            psf_flux_err_theory[psf_flux_err_theory==0.0] = np.nan
            props["flux_err_ratio_psf_theory"] = df_sub["psf_flux_err"].values / psf_flux_err_theory
            return props

        df_props = compute_properties(df_pts)

        # 9. Calculate and append median, RMS, and NMAD metrics
        for prop in properties:
            exp_val = E_p[prop]
            for bin_name, cond in [("bright", cond_bright), ("faint", cond_faint)]:
                vals = df_props[prop][cond]
                vals=vals[np.isfinite(vals)]
                # can be set higher to have robust statistics
                if len(vals) <= 1:
                    median_val = np.nan
                    rms_val = np.nan
                    nmad_val = np.nan
                else:
                    median_val = float(np.median(vals))
                    rms_val = float(np.sqrt(np.mean((vals - exp_val)**2)))
                    nmad_val = float(1.4826 * np.median(np.abs(vals - exp_val)))

                self.append_data(f"{prop}_{bin_name}_median", median_val, "")
                self.append_data(f"{prop}_{bin_name}_rms", rms_val, "")
                self.append_data(f"{prop}_{bin_name}_nmad", nmad_val, "")



    def evaluate_metrics(self):
        """
        Evaluate metrics against validity (checking they are not None and finite).
        """
        for metric_name, card in self.data.items():
            is_valid = self.is_valid_metric(metric_name, card.data_value)
            if is_valid:
                self.add_evaluation(metric_name, True)
