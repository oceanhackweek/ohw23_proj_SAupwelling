"""
Utility functions to be reused in notebooks.
"""
import fsspec
import numpy as np
import s3fs
import xarray as xr


def extract_file_id_from_filename(filename):
    """
    Extract the file ID from a filename.

    Filename must follow the structure of IMOS data in S3 buckets.
    """
    return filename.split('/')[6].split('-')[2]


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
    files : dicti
        dict of files matching the pattern.
    """
    fs = fsspec.filesystem('s3',use_listings_cache=False,anon=True,)
    if not path.endswith("/"):
        path = path + "/"
    files = fs.glob(f"{path}{pattern}")

    # Sort the files by date
    files = np.sort(files)

    # Extract the unique file IDs
    file_ids = [extract_file_id_from_filename(file) for file in files]
    file_ids = np.unique(file_ids)

    first_ref_files = []

    # Loop through eacy unique file ID
    for file_id in file_ids:
        # Filter all the files with that ID
        filtered_list = filter(lambda file_: file_.split('/')[6].split('-')[2] == file_id, files)
        filtered_list = sorted(filtered_list)
        # Select just the first one
        first = next(iter(filtered_list), None)
        # Add file name to list
        first_ref_files.append(first)

    output = {
        "files" : files,
        "file_ids": file_ids,
        "first_ref_files": first_ref_files
    }

    return output


def open_cdt(url, variable='TEMP'):
    """
    Open a CDT file from an S3 bucket.

    Parameters
    ----------
    url : str
        URL to the file.
    variable : str
        Variable to load.
        
    """
    s3 = s3fs.S3FileSystem(anon=True,default_fill_cache=False,default_cache_type=None)
    with s3.open(url,) as f:
        data=xr.open_dataset(f,engine='h5netcdf').load().squeeze()
        data[variable] = data[variable][data.TEMP_quality_control==1]
    return data