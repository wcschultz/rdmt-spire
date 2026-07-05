import os

import asdf
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..constants.codes import StatusCodes
from ..db_tables.sci_tables import L2ScienceResultsTable
from ..manager import MonitorManager


def test_source_catalog_integration(tmp_path):
    """
    Integration test for SourceCatalogMonitor with MonitorManager and database archiving.
    """
    # 1. Define temporary data directory and paths
    datadir = str(tmp_path)
    filename = "mock_file_cal.asdf"
    parquet_filename = "mock_file_cat.parquet"
    parquet_path = os.path.join(datadir, parquet_filename)

    # 2. Build a valid ASDF object referencing our mock filename
    af = asdf.AsdfFile()
    af.tree["roman"] = {
        "meta": {
            "filename": filename,
            "instrument": {
                "optical_element": "F087"
            },
            "exposure": {
                "exposure_time": 294.10974
            }
        }
    }

    # 3. Create mock parquet catalog data with 4 known point sources
    data = {
        'is_extended': [False, False, False, False],
        'psf_flux': [36307.805, 14454.398, 5754.399, 2290.868],
        'psf_flux_err': [233.1558, 221.6841, 188.6324, 183.4854],
        'sharpness': [0.2, 0.4, 0.1, 0.3],
        'roundness1': [-0.1, 0.3, -0.2, 0.4],
        'ellipticity': [0.1, 0.3, 0.2, 0.4],
        'fluxfrac_radius_50': [0.5, 0.7, 0.4, 0.6],
        'aper01_flux': [1000.0, 1000.0, 1000.0, 1000.0],
        'aper02_flux': [2000.0, 3000.0, 1500.0, 2500.0],
        'aper04_flux': [3000.0, 6000.0, 2250.0, 5000.0],
        'aper08_flux': [4000.0, 12000.0, 3375.0, 10000.0]
    }
    df = pd.DataFrame(data)
    df.to_parquet(parquet_path)

    # 4. Initialize MonitorManager
    monitor_config = {
        "source_catalog": {
            "datadir": datadir
        }
    }
    manager = MonitorManager(af, "source_catalog", monitor_config=monitor_config)

    # 5. Process the monitor
    manager.process()
    assert manager.statusCode == StatusCodes.SUCCESS
    assert len(manager.monitor_objects) == 1
    assert manager.monitor_objects[0].monitor_name == "source_catalog"

    # 6. Initialize in-memory SQLite database session
    engine = create_engine("sqlite:///:memory:")
    session_local = sessionmaker(bind=engine)
    L2ScienceResultsTable.__table__.create(bind=engine)
    session = session_local()

    try:
        # 7. Archive the results
        reprocess_number = 0
        manager.archive(session, filename, reprocess_number, L2ScienceResultsTable)

        # 8. Retrieve the stored row and assert values
        row = session.get(L2ScienceResultsTable, (filename, reprocess_number))
        assert row is not None
        assert row.num_sources_bright == 2
        assert row.num_sources_faint == 2
        assert row.sharpness_bright_median == pytest.approx(0.3)
        assert row.sharpness_bright_median_eval is True
        assert row.sharpness_faint_median == pytest.approx(0.2)
        assert row.sharpness_faint_median_eval is True

        # 9. Verify database verification works
        # Check that comparing the row against itself passes
        assert row._verify(row, return_result=True) is True

    finally:
        session.close()
