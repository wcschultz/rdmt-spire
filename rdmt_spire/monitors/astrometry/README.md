# astrometry monitor
The monitor selects stars from input catalog with magnitude in a user specified band
 being less than  a user specified threshold.
 ```
 params['photometric_band'] = 'F106'
 params['magnitude_threshold']= 17.0
 ```
 It does PSF photometry to estimate position of selected stars,
starting with true coordinates based on the input catalog. 
The metrics computed by the monitor are 
- **astrometric_offset**: RMS separation [arcsec] between estimated and true coordinates of stars based on the input catalog 
- **num_astrometric_source**: Number of sources used to compute the astrometric offset

## Implementation details
In addition to the input file, this monitor requires some additional data files to do its job. 
The `datadir` variable sets the root data folder (or s3 bucket). The various data files 
are organized as shown below. 
```text
root-data-dir/
|-- astrometry/
|   |-- input_catalogs/
|   |   |-- p00032/
|   |   |   |-- meta.yaml	
|   |   |   +-- cat-0.parquet
|   |   |-- p00555/
|   |   |   |-- meta.yaml	
|   |   |   +-- cat-0.parquet
|   |   |   +-- cat-1.parquet
|   |   |   +-- .............
|   |   |   +-- cat-N.parquet
|   +-- wfi_stpsf_grid_n9o4.asdf
```

The two main categories of addditional files are
## PSF 
``'epsf_image_name':'astrometry/wfi_stpsf_grid_n9o4.asdf'``
## Input Catalog
`` 'input_catalogs':'astrometry/input_catalogs'``

The input catalog for each program is in its own seprate folder. 
The program number is given by the first 5 digits of the filename, for further details see 
[RDocs](https://roman-docs.stsci.edu/data-handbook/wfi-data-levels-and-products#WFIDataLevelsandProducts-WFIFileNamingConventions).
For a typical input file with filename ``r0003201001001001004_0001_wfi01_f106_cal.asdf``
the program number is 32. The files are stored in parquet format. 
Whole catalog is split across multiple parquet files, with each file holding data corresponding to a given healpix. The healpix parameters used for chunking are specified via `meta.yaml`
```text
nside: 512
format: parquet
frame: galactic
nest: True
```
The supported frames are galactic and equatorial. The nside should be set to 0, if we only have one catalog file. 

Multiple program_no could be using same catalog. So we hard wire this using a dictionary which maps the program no to the input catalog directory. This is less than ideal and can be removed in future
if we guarantee that programs with same program number have same input catalog.
```
key_names = {32: "p00032", 555: "p00555"}
```

Each parquet file contains a table with following schema
- {name: ra, datatype: float64, unit: degree}
- {name: dec, datatype: float64, unit: degree}
- {name: type, datatype: string, ['PSF', 'SER']}
- {name: F062, datatype: float64, unit: maggie}
- {name: F087, datatype: float64, unit: maggie}
- {name: F106, datatype: float64, unit: maggie}
- {name: F129, datatype: float64, unit: maggie}
- {name: F146, datatype: float64, unit: maggie}
- {name: F158, datatype: float64, unit: maggie}
- {name: F184, datatype: float64, unit: maggie}
- {name: F213, datatype: float64, unit: maggie}

Only type with 'PSF' are used. 
The flux are in maggie.  For a star with magnitude $m$, the flux in maggie is given by $10.0^{-0.4*m}$.


