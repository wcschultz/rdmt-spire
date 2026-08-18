"""Thresholds for source catalog monitor metrics.

These thresholds are intended for metric names ending in ``_median`` and ``_std``
for both bright and faint source bins. Values are placeholders and should be
refined with calibration data.
"""

SOURCE_CATALOG_PROPERTIES = [
    "sharpness_bright",
    "roundness1_bright",
    "ellipticity_bright",
    "flux_frac_radius_50_bright",
    "flux_ratio_aper01_aper02_bright",
    "flux_ratio_aper02_aper04_bright",
    "flux_ratio_aper04_aper08_bright",
    "flux_err_ratio_psf_theory_bright",
    "sharpness_faint",
    "roundness1_faint",
    "ellipticity_faint",
    "flux_frac_radius_50_faint",
    "flux_ratio_aper01_aper02_faint",
    "flux_ratio_aper02_aper04_faint",
    "flux_ratio_aper04_aper08_faint",
    "flux_err_ratio_psf_theory_faint",
]

SOURCE_CATALOG_STATISTICS = ["n_sources", "median", "dispersion_p68", "dispersion_p95", "mean", "std"]
#FILTERS = ['f062', 'f087','f106', 'f129', 'f146', 'f158', 'f184', 'f213']
    