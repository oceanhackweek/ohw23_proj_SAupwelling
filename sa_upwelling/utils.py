"""
Utility functions to be reused in notebooks.
"""
import fsspec
import s3fs
import xarray as xr
from dask import bag as db


def extract_file_id_from_filename(filename):
    """
    Extract the file ID from a filename.

    Filename must follow the structure of IMOS data in S3 buckets.
    """
    return filename.split("/")[6].split("-")[2]


def load_files(path="s3://imos-data/IMOS/ANMN/NRS/NRSKAI/Temperature/", pattern="*.nc"):
    """Load files from an S3 bucket that match a pattern.

    Parameters
    ----------
    path : str
        Path to the directory containing the files.
    pattern : str
        Pattern to match the files.

    Returns
    -------
    first_ref_files : list
        list of the first files that match the file ID.
    """
    fs = fsspec.filesystem(
        "s3",
        use_listings_cache=False,
        anon=True,
    )
    if not path.endswith("/"):
        path = path + "/"
    files = sorted(fs.glob(f"{path}{pattern}"))

    # Extract the unique file IDs
    file_ids = {extract_file_id_from_filename(file) for file in files}

    # Get only the first file of each file ID
    files = {
        file_id_: sorted(
            [
                file_
                for file_ in files
                if extract_file_id_from_filename(file_) == file_id_
            ]
        )[0]
        for file_id_ in file_ids
    }

    return files


def open_nc(url, variable="TEMP"):
    """
    Open an nc file from an S3 bucket.

    Parameters
    ----------
    url : str
        URL to the file.
    variable : str
        Variable to load.

    Returns
    -------
    data : xarray.Dataset
    """
    s3 = s3fs.S3FileSystem(anon=True, default_fill_cache=False, default_cache_type=None)
    with s3.open(
        url,
    ) as f:
        data = xr.open_dataset(f, engine="h5netcdf").load().squeeze()
        data[variable] = data[variable][data.TEMP_quality_control == 1]
    return data


def open_files_with_dask(files):
    """
    Open files with dask bag. Requires a running Dask client.

    Parameters
    ----------
    files : list
        List of files to open.

    Returns
    -------
    bag : dask.bag
    cast : list of xarray Datasets.
    """
    bag = db.from_sequence(files)
    cast = db.map(open_nc, bag).compute()
    return cast


def get_shared_coordinates(list_of_xr_datasets):
    """
    Get shared coordinates between a list of xarray datasets.

    Parameters
    ----------
    list_of_xr_datasets : list
        List of xarray datasets.

    Returns
    -------
    commonvars: list
        List of shared coordinates.
    """
    return list(
        set.intersection(
            *list(
                (
                    map(
                        lambda ds: set([var for var in ds.data_vars]),
                        list_of_xr_datasets,
                    )
                )
            )
        )
    )
