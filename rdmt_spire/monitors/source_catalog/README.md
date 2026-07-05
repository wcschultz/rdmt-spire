# L4 Source Catalog Monitor
This monitor will read the source catalog created by running romancal on an L2 file. The source catalog contains position and photometric information of both stars and galaxies. A metric is constructed from the available information, e.g, median and standard deviation of radius for a given enricled energy fraction, etc. Such statistics can be useful to track the performance of the Roman WFI. 

## Implementation details
The monitor takes as input and L2 image file.
The source catalog file name is derived from the base L2 image filename (`asdf_file['roman']['meta']['filename']`) by replacing suffix `_cal.asdf` with `_cat.parquet`. The path to the source catalog file is passed in through an extra parameter `datadir`.

### Identification of point sources 
Extended sources are not useful for tracking performance as we do not know their intrinsic brightness profile. Thus, the first step is to identify point sources. The `is_extended` flag can be used to identify point sources. Alternatively, to have more more user control one can use other criteria. For example, a source can be  classified as point like if its, flux ratio ``(aper04_flux/aper02_flux)`` is less than 1.2 (the theoretically expected ratio based on the known PSF), encircled energy fraction ``fluxfrac_radius_50`` is less than the theoretically expected value, and ``kron_radius`` is less than 0.17. 

### Source Properties
 We track the following source properties. The first three are related to the shape of the source, while the last four are related to the flux of the source. 
One can include more properties. Properties are calculated from the columns available in the source catalog table.
For a detailed list of columns available in the source catalog table see [romancal documenation](https://roman-pipeline.readthedocs.io/en/stable/roman/source_catalog/main.html#source-photometry-and-properties). 


|Property name   | Calculation with column names     | Description|
|----------------|-----------------|-----|
| sharpness      | sharpness       |     |
| roundness1     | roundness1      |     |
| ellipticity    | ellipticity     |     |
| flux_frac_radius_50 | flux_frac_radius_50 |Encircled Energy at 50% radius |     
| flux_ratio_aper01_aper02| aper02_flux/aper01_flux | Aperture flux ratio |     |
| flux_ratio_aper02_aper04| aper04_flux/aper02_flux | Aperture flux ratio |     |
| flux_ratio_aper04_aper08| aper08_flux/aper04_flux | Aperture flux ratio |     |
| flux_err_ratio_psf_theory |psf_flux_err/psf_flux_err_theory | Ratio of measured to expected PSF flux error |

The `psf_flux_err_theory` (in nJy) is estimated from
$$\sigma_f = \frac{\sqrt{t_{\rm exp}(n_{\rm eff}f_{\rm bkgd}+f_{\rm source})}}{t_{\rm exp}}$$
where $f_{\rm source}$ is the flux (in e/s) from the source $f_{\rm bkgd}$ is the background flux (in e/s), and $n_{\rm eff}$ is the effective number of pixels under the PSF.
We assume $$f_{\rm bkgd}=2 f_{\rm min-Zodiacal} +f_{\rm thermal}$$
The values of $n_{\rm eff}$, $f_{\rm min-Zodiacal}$ and $f_{\rm thermal}$ vary with optical element and were adopted from the [Roman technical documents](https://science.nasa.gov/mission/roman-space-telescope/wfi-technical/).
To convert the flux in e/s to nJy we multipy by factor 
$\kappa=10^{(31.4-Z_p)/2.5}$.

### Metric
We compute the median and the deviation of various source properties from the excpected values. The deviation is quantified using root mean square (RMS) and normalized-median-absolute-deviation (NMAD). The excpected values were estimated from simulations done using *romanisim* separately for each optical element. These are provided via file `expected_photometric_properties.csv`

### Magnitude Ranges
The photometric properties are expected to vary with brightness of the sources and the expsoure time. Two limits are of particular interest, the faint end (below which we cannot reliably measure the source properties due to low SNR) and the bright end (related to saturation effects). 
The saturation magnitude for filter with central wavelength $\lambda$ is given by $$m_{\rm sat} = Z_p(\lambda) -2.5 \log \alpha_{\rm sat}$$ where  $\alpha_{\rm sat}$ is the charge accumulated at saturation and is given by $$\alpha_{\rm sat}=\frac{C_{\rm sat}}{f_{\rm peak}(\lambda)t_{\rm exp}}$$ where  $t_{\rm exp}$ is the exposure time, $f_{\rm peak}(\lambda)$ is the fraction of counts in the peak pixel and the $C_{\rm sat}=120,000\ e^{-}$ is the charge in electrons at the full well depth. 

Assuming that at the faint end the SNR is background dominated. 
The Signal to Noise (SNR) ratio is given by $$SNR = \frac{f_{\rm source}}{\sigma_f} = \frac{f_{\rm source} t_{\rm exp}}{\sqrt{t_{\rm exp}\left(n_{\rm eff}f_{\rm bkgd} + f_{\rm source}\right)}}$$.
This is a quadratic equation in terms of the variable $f_{\rm source}$. 
  We estimate the faint limit $m_{\rm faint}$ by solving the SNR equation for $f_{\rm source}$ at $SNR=50$, which matches the faintest source detectable by the roman photometry pipeline.
We select sources with magnitude $m$ lying between $m_{\rm sat}<m< m_{\rm faint}$.
The value of $m_{\rm faint}-m_{sat}$ is typically around 5 mags. Hence, we subdivide the sources into a bright bin $m_{\rm sat}<m<(m_{\rm sat}+m_{\rm faint})/2$ and a faint bin $(m_{\rm sat}+m_{\rm faint})/2 < m < m_{\rm faint}$.



| Parameter | Table| Column Name | Units|
|-----------|------|-------------|------|
| $Z_p$     |  zero_points.csv| Z_R         | mag |
| $n_{\rm eff}$ | filter_parameters.ecsv | center_PSF_n_eff_pixel | pixels |
| $f_{\rm peak}$ | filter_parameters.ecsv | center_PSF_peak_flux | fraction |
| $f_{\rm thermal}$ | internal_thermal_backgrounds.ecsv | rate | e/s |
| $f_{\rm min-Zodiacal}$ | zodiacal_light.ecsv | rate | e/s |


