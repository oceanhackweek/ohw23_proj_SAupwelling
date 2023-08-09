"""
Utility functions to be reused in notebooks.
"""
from glob import glob
import fsspec
import s3fs
import xarray as xr
from dask import bag as db


# List of moorings and corresponding regions to build S3 paths
DEFAULT_MOORINGS = [
    ("NRS", "NRSKAI"),
    ("SA", "SAM8SG"),
    ("SA", "SAM5CB"),
    ("SA", "SAM2CP"),
    ("SA", "SAM6IS"),
    ("SA", "SAM3MS"),
    ("SA", "SAM7DS")
]


def extract_file_id_from_filename(filename):
    """
    Extract the file ID from a filename.

    Filename must follow the structure of IMOS data in S3 buckets.
    """
    return filename.split("/")[6].split("-")[2]


def load_file_urls(path="s3://imos-data/IMOS/ANMN/NRS/NRSKAI/Temperature/", pattern="*.nc", get_file_ids=False, get_first_file_only=False):
    """Load files from an S3 bucket that match a pattern.

    Parameters
    ----------
    path : str
        Path to the directory containing the files.
    pattern : str
        Pattern to match the files.
    get_file_ids : bool
        If turned on, create a list of lists where each list has a specific file ID.

    Returns
    -------
    files : list
        List of files that match the path and pattern.
    """
    fs = fsspec.filesystem(
        "s3",
        use_listings_cache=False,
        anon=True,
    )
    if not path.endswith("/"):
        path = path + "/"
    files = sorted(fs.glob(f"{path}{pattern}"))
    
    if get_file_ids:
        file_ids = dict()
        for file in files:
            file_id = extract_file_id_from_filename(file)
            if not file_ids.get(file_id, False):
                file_ids[file_id] = []
            else:
                file_ids[file_id].append(file)
                
        files = sorted(list(file_ids.values()))
        
    if get_first_file_only:
        files = [file[0] if isinstance(file, list) else file for file in files]

    return files


def open_nc(url_or_path, variable=None, remote=True):
    """
    Open an nc file from an S3 bucket or locally.

    Parameters
    ----------
    url_or_path : str
        URL or path to the file.
    remote : bool
        Whether to load from S3 or locally

    Returns
    -------
    data : xarray.Dataset
    """
    if remote:
        s3 = s3fs.S3FileSystem(anon=True, default_fill_cache=False, default_cache_type=None)
        with s3.open(
            url_or_path,
        ) as f:
            data = xr.open_dataset(f, engine="h5netcdf").load().squeeze()
    else:
        data = xr.open_dataset(url_or_path, engine="h5netcdf").load().squeeze()
            
    return data


def open_files_with_dask(files):
    """
    Open files with dask bag. Requires a running Dask client.

    Parameters
    ----------
    files : list
        List of file URLs to open.

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


def load_data_products(moorings=moorings, data_type="hourly-timeseries", pattern=None, data_dir="../Datasets/"):
    """
    Load data products from S3 buckets or locally.

    Parameters
    ----------
    moorings : list
        List of tuples (region, mooring_ID) to load.
    data_type : str
        Data type to load, e.g. "aggregated_timeseries", "hourly_timeseries".
    pattern : str
        Pattern to match the files.
    """
    data_type = "hourly-timeseries"
    files, ds = dict(), dict()

    if pattern is None:
        pattern = f"*_{data_type}_*.nc"

    if not data_dir.endswith("/"):
        data_dir = data_dir + "/"

    # Find file URLs on S3 or load local files
    for region, mooring in moorings:
        
        # Check if file exists
        glob_path = glob(f"{data_dir}/{region}/{mooring}/{pattern}")
        local = len(glob_path) > 0
        
        # Retrieve from remote if they don't exist
        if not local:
            print(f"Geting URLs of {data_type} for mooring '{mooring}'.")
            path = f"s3://imos-data/IMOS/ANMN/{region}/{mooring}/{data_type.replace('-', '_')}/"
            file_url = load_file_urls(path, pattern=f"{pattern}")[0]
            files[mooring] = file_url        
        # Load them locally if they exist
        else:
            print(f"Loading local {data_type} data for mooring '{mooring}'.")
            file_url = glob_path[0]
            files[mooring] = file_url
        
        outfile = f"{data_dir}/{region}/{mooring}/" + file_url.split("/")[-1]
        ds[mooring] = open_nc(outfile if local else file_url, remote=not local)
        
        # Write files locally if they don't exist
        if not local:
            ds[mooring].to_netcdf(outfile)
    
    return files, ds
