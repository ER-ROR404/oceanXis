"""Copernicus Marine Toolbox ingestion wrapper.

The ONLY module that knows about copernicusmarine credentials and API.
All other modules import from here.

Usage:
    client = CopernicusClient.from_env()
    ds = client.describe(dataset_id="METOFFICE-GLO-SST-L4-REP-OBS-SST")
    result = client.subset(
        dataset_id="METOFFICE-GLO-SST-L4-REP-OBS-SST",
        variable="analysed_sst",
        region_bounds=bay_of_bengal,
        start_date="2024-01-01",
        end_date="2024-01-01",
        output_path="data/raw/sst_2024-01-01.nc",
    )
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import copernicusmarine
import xarray as xr

from .regions import RegionBounds

logger = logging.getLogger(__name__)


@dataclass
class SubsetResult:
    """Result of a Copernicus subset operation.

    Attributes:
        dataset_id: Dataset that was subset.
        variable: Variable(s) downloaded.
        output_path: Path to the downloaded file.
        shape: Tuple of (time, lat, lon) dimensions from the downloaded dataset.
        success: Whether the download completed without error.
        error: Error message if the download failed.
    """

    dataset_id: str
    variable: str
    output_path: Optional[Path]
    shape: Optional[tuple[int, int, int]] = None
    success: bool = True
    error: Optional[str] = None


class CopernicusClient:
    """Wrapper around copernicusmarine with credentials management.

    Credentials are read from environment variables:
        COPERNICUSMARINE_SERVICE_USERNAME
        COPERNICUSMARINE_SERVICE_PASSWORD

    Or can be passed explicitly.
    """

    def __init__(self, username: str, password: str) -> None:
        """Initialize with explicit credentials.

        Args:
            username: Copernicus Marine username.
            password: Copernicus Marine password.
        """
        self.username = username
        self.password = password

    @classmethod
    def from_env(cls) -> CopernicusClient:
        """Create client from COPERNICUSMARINE_SERVICE_* environment variables.

        Raises:
            ValueError: If either credential is missing.
        """
        username = os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME", "")
        password = os.environ.get("COPERNICUSMARINE_SERVICE_PASSWORD", "")
        if not username or not password:
            raise ValueError(
                "Copernicus credentials not found. Set COPERNICUSMARINE_SERVICE_USERNAME "
                "and COPERNICUSMARINE_SERVICE_PASSWORD in .env"
            )
        return cls(username=username, password=password)

    def describe(
        self,
        dataset_id: str,
        show_all_versions: bool = False,
    ) -> dict:
        """Describe a Copernicus Marine dataset (RULE 7 verification).

        Args:
            dataset_id: The dataset identifier.
            show_all_versions: If True, show all versions.

        Returns:
            Dict with dataset metadata (variables, coverage, resolution, etc.).
        """
        logger.info("Describing dataset: %s", dataset_id)
        try:
            catalogue = copernicusmarine.describe(
                dataset_id=dataset_id,
                show_all_versions=show_all_versions,
                username=self.username,
                password=self.password,
            )
            # Convert to dict for easy consumption
            if hasattr(catalogue, "model_dump"):
                return catalogue.model_dump()
            return {"raw": str(catalogue)}
        except Exception as e:
            logger.error("Failed to describe dataset %s: %s", dataset_id, e)
            raise

    def subset(
        self,
        dataset_id: str,
        variable: str,
        region_bounds: RegionBounds,
        start_date: str,
        end_date: str,
        output_path: Optional[str | Path] = None,
        output_dir: Optional[str | Path] = None,
        file_format: str = "netcdf",
        minimum_depth: Optional[float] = None,
        maximum_depth: Optional[float] = None,
        dry_run: bool = False,
    ) -> SubsetResult:
        """Download a subset of a Copernicus Marine dataset.

        Args:
            dataset_id: Dataset identifier.
            variable: Variable name(s) to download (comma-separated for multiple).
            region_bounds: Geographic bounding box.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            output_path: Full path for output file (mutually exclusive with output_dir).
            output_dir: Directory for output file (name auto-generated).
            file_format: Output format (netcdf, zarr, csv, parquet).
            minimum_depth: Minimum depth for 3D datasets (meters).
            maximum_depth: Maximum depth for 3D datasets (meters).
            dry_run: If True, only compute what would be downloaded without actually downloading.

        Returns:
            SubsetResult with download status and metadata.
        """
        bbox = region_bounds.as_copernicus_bbox()
        variables = [v.strip() for v in variable.split(",")]

        kwargs = {
            "dataset_id": dataset_id,
            "variables": variables,
            "minimum_longitude": bbox["minimum_longitude"],
            "maximum_longitude": bbox["maximum_longitude"],
            "minimum_latitude": bbox["minimum_latitude"],
            "maximum_latitude": bbox["maximum_latitude"],
            "start_datetime": start_date,
            "end_datetime": end_date,
            "username": self.username,
            "password": self.password,
            "file_format": file_format,
            "dry_run": dry_run,
        }

        if minimum_depth is not None:
            kwargs["minimum_depth"] = minimum_depth
        if maximum_depth is not None:
            kwargs["maximum_depth"] = maximum_depth

        # Output path handling — copernicusmarine.subset uses output_filename or output_directory
        if output_path is not None:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            kwargs["output_filename"] = str(output_path)
        elif output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            kwargs["output_directory"] = str(output_dir)

        logger.info(
            "Subsetting %s [%s] for %s–%s, region=%s",
            dataset_id,
            variable,
            start_date,
            end_date,
            region_bounds.id,
        )

        try:
            response = copernicusmarine.subset(**kwargs)

            if dry_run:
                return SubsetResult(
                    dataset_id=dataset_id,
                    variable=variable,
                    output_path=None,
                    success=True,
                )

            # ResponseSubset has file_path attribute with the actual downloaded file
            actual_path = None
            if hasattr(response, "file_path") and response.file_path:
                actual_path = Path(response.file_path)
            elif hasattr(response, "filename") and response.filename:
                # Fallback: construct path from output_dir + filename
                base = output_dir if output_dir else Path(".")
                actual_path = base / response.filename

            # Read shape if file exists
            shape = None
            if actual_path and actual_path.exists():
                try:
                    ds = xr.open_dataset(actual_path)
                    dims = dict(ds.dims)
                    shape = (
                        dims.get("time", dims.get("t", 1)),
                        dims.get("latitude", dims.get("lat", 0)),
                        dims.get("longitude", dims.get("lon", 0)),
                    )
                    ds.close()
                except Exception as e:
                    logger.warning("Could not read shape from %s: %s", actual_path, e)

            return SubsetResult(
                dataset_id=dataset_id,
                variable=variable,
                output_path=actual_path,
                shape=shape,
                success=True,
            )

        except Exception as e:
            logger.error("Subset failed for %s: %s", dataset_id, e)
            return SubsetResult(
                dataset_id=dataset_id,
                variable=variable,
                output_path=None,
                success=False,
                error=str(e),
            )

    def subset_split(
        self,
        dataset_id: str,
        variable: str,
        region_bounds: RegionBounds,
        start_date: str,
        end_date: str,
        output_dir: str | Path,
        split_on_time: Optional[str] = "day",
        file_format: str = "netcdf",
        minimum_depth: Optional[float] = None,
        maximum_depth: Optional[float] = None,
        concurrent_processes: Optional[int] = None,
    ) -> list[SubsetResult]:
        """Chunked download via subset_split_on (for large date ranges).

        Args:
            dataset_id: Dataset identifier.
            variable: Variable name(s) to download.
            region_bounds: Geographic bounding box.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            output_dir: Directory for output files.
            split_on_time: Split dimension (hour, day, month, year).
            file_format: Output format.
            minimum_depth: Minimum depth for 3D datasets.
            maximum_depth: Maximum depth for 3D datasets.
            concurrent_processes: Number of parallel download processes.

        Returns:
            List of SubsetResult for each chunk.
        """
        bbox = region_bounds.as_copernicus_bbox()
        variables = [v.strip() for v in variable.split(",")]

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        kwargs = {
            "dataset_id": dataset_id,
            "variables": variables,
            "minimum_longitude": bbox["minimum_longitude"],
            "maximum_longitude": bbox["maximum_longitude"],
            "minimum_latitude": bbox["minimum_latitude"],
            "maximum_latitude": bbox["maximum_latitude"],
            "start_datetime": start_date,
            "end_datetime": end_date,
            "username": self.username,
            "password": self.password,
            "file_format": file_format,
            "output_directory": str(output_dir),
        }

        if minimum_depth is not None:
            kwargs["minimum_depth"] = minimum_depth
        if maximum_depth is not None:
            kwargs["maximum_depth"] = maximum_depth

        logger.info(
            "Chunked subset %s [%s] for %s–%s, split_on=%s",
            dataset_id,
            variable,
            start_date,
            end_date,
            split_on_time,
        )

        try:
            responses = copernicusmarine.subset_split_on(
                on_time=split_on_time,
                concurrent_processes=concurrent_processes,
                **kwargs,
            )

            results = []
            for resp in responses:
                actual_path = None
                if hasattr(resp, "output_file"):
                    actual_path = Path(resp.output_file)
                results.append(
                    SubsetResult(
                        dataset_id=dataset_id,
                        variable=variable,
                        output_path=actual_path,
                        success=True,
                    )
                )

            logger.info("Chunked download complete: %d files", len(results))
            return results

        except Exception as e:
            logger.error("Chunked subset failed for %s: %s", dataset_id, e)
            return [
                SubsetResult(
                    dataset_id=dataset_id,
                    variable=variable,
                    output_path=None,
                    success=False,
                    error=str(e),
                )
            ]
