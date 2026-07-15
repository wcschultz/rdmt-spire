from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..constants.database import (
    ARCHIVE_LENGTH,
    DATA_RELEASE_ID_LENGTH,
    DETECTOR_LENGTH,
    FILENAME_LENGTH,
    OBSERVATION_ID_LENGTH,
    OPTICAL_ELEMENT_LENGTH,
    SOFTWARE_VERSION_LENGTH,
    VISIT_ID_LENGTH,
)
from ..constants.dmd import FileTypes
from .base import Base, ResultsBase


class L2ScienceMetaTable(Base):
    """Class containing schema for the L2 Science data metadata table."""

    __tablename__ = "l2_science_meta"
    # Information from the DMD SNS notification
    filename:               Mapped[str] = mapped_column(String(FILENAME_LENGTH), primary_key=True) # body['filename']
    reprocess_number:       Mapped[int] = mapped_column(Integer(), primary_key=True) # determined from body['reprocessingState]
    # 0 for prompt (reprocessingState = None), 
    # +1 for each reprocessing (reprocessingState = 'reprocessed' or 'data_release')
    program_number:         Mapped[int] = mapped_column(Integer()) # from filename
    exposure_number:        Mapped[int] = mapped_column(Integer()) # from filename
    visit_id:               Mapped[str] = mapped_column(String(VISIT_ID_LENGTH)) # from filename
    detector:               Mapped[str] = mapped_column(String(DETECTOR_LENGTH)) # from filename
    optical_element:        Mapped[str] = mapped_column(String(OPTICAL_ELEMENT_LENGTH)) # from filename
    archive_bucket:         Mapped[str] = mapped_column(String(ARCHIVE_LENGTH)) # from body['archiveBucket']
    archive_key:            Mapped[str] = mapped_column(String(ARCHIVE_LENGTH)) # from body['archiveObjectKey']
    file_created_datetime:  Mapped[datetime] = mapped_column(DateTime()) # from body['fileCreationTimestamp']
    dmd_notify_datetime:    Mapped[datetime] = mapped_column(DateTime()) # from outer message structure
    data_release_id:        Mapped[Optional[str]] = mapped_column(String(DATA_RELEASE_ID_LENGTH))

    # Information that requires opening the file to extract
    observation_id:         Mapped[Optional[str]] = mapped_column(String(OBSERVATION_ID_LENGTH)) # from meta.observation.observation_id
    exp_start_datetime:     Mapped[Optional[datetime]] = mapped_column(DateTime()) # from meta.exposure.start_time
    romancal_version:       Mapped[Optional[str]] = mapped_column(String(SOFTWARE_VERSION_LENGTH)) # from meta.calibration_software_version
    crds_context:           Mapped[Optional[str]] = mapped_column(String(SOFTWARE_VERSION_LENGTH)) # from meta.ref_file.crds.context
    sdf_version:            Mapped[Optional[str]] = mapped_column(String(SOFTWARE_VERSION_LENGTH)) # from meta.sdf_software_version

    # Information populated by RDMT
    monitor_end_datetime:   Mapped[Optional[datetime]] = mapped_column(DateTime()) # populated by Spire
    # Below are the monitor completion checks:
    # -1 indicates the monitor should not be run
    # 0 indicates the monitor still needs to be run
    # 1 indicates the monitor ran successfully
    essential_status:       Mapped[int] = mapped_column(Integer(), default=0) # populated by Spire
    persistence_status:     Mapped[int] = mapped_column(Integer(), default=0) # populated by Spire
    comprehensive_status:   Mapped[int] = mapped_column(Integer(), default=-1) # populated by Spire
    
    # for testing
    astrometry_status:      Mapped[int] = mapped_column(Integer(), default=0) # populated by Spire
    noise_1f_status:        Mapped[int] = mapped_column(Integer(), default=0) # populated by Spire

    def _get_verification_columns(self):
        return [
            "filename",
            "reprocess_number",
            "program_number",
            "exposure_number"
            "visit_id",
            "detector",
            "optical_element",
            "archive_bucket",
            "archive_key",
            "file_created_datetime",
            "dmd_notify_datetime",
            "data_release_id",
            "observation_id",
            "exp_start_datetime",
            "romancal_version",
            "crds_context",
            "sdf_version",
            "monitor_end_datetime",
            "essential_status",
            "comprehensive_status",
            "persistence_status",
            "astrometry_status",
        ]
    
    @property
    def file_type(self):
        # Used for mapping the table classes to the file types they relate to
        return FileTypes.L2_SCIENCE
    

class L2ScienceResultsTable(ResultsBase):
    """Class containing schema for the L2 Science data monitoring results table."""

    __tablename__ = "l2_science_results"
    filename:                   Mapped[str] = mapped_column(String(FILENAME_LENGTH), primary_key=True) # from DMD notification
    reprocess_number:           Mapped[int] = mapped_column(Integer(), primary_key=True) # from DMD notification
    # 0 for prompt (reprocessingState = None), 
    # +1 for each reprocessing (reprocessingState = 'reprocessed' or 'data_release') reprocessing

    # Astrometry monitor results
    astrometric_offset:         Mapped[Optional[float]] = mapped_column(Float())
    astrometric_offset_eval:    Mapped[Optional[bool]] = mapped_column(Boolean())
    num_astrometric_sources:        Mapped[Optional[int]] = mapped_column(Integer())
    num_astrometric_sources_eval:   Mapped[Optional[bool]] = mapped_column(Boolean())

    # 1/f Noise monitor results
    noise_1f_power_ratio:       Mapped[Optional[float]] = mapped_column(Float())
    noise_1f_power_ratio_eval:  Mapped[Optional[bool]] = mapped_column(Boolean())

    def _get_verification_columns(self):
        return [
            "filename",
            "reprocess_number",
            "astrometric_offset",
            "astrometric_offset_eval",
            "num_astrometric_sources",
            "num_astrometric_sources_eval",
            "noise_1f_power_ratio",
            "noise_1f_power_ratio_eval",
        ]

    @property
    def file_type(self):
        # Used for mapping the table classes to the file types they relate to
        return FileTypes.L2_SCIENCE