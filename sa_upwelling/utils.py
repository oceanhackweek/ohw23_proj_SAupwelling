"""
Utility functions to be reused in notebooks.
"""
from glob import glob
import fsspec
import s3fs
import xarray as xr
from dask import bag as db
from pathlib import Path
import pandas as pd
import numpy as n
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns


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


def load_data_products(moorings=DEFAULT_MOORINGS, data_type="hourly-timeseries", pattern=None, data_dir="../Datasets/"):
    """
    Load data products from S3 buckets or locally.

    Usage:
        hourly_files, hourly_ds = utils.load_data_products()
        agg_files, agg_ds = utils.load_data_products(data_type="aggregated_timeseries",
                                                     pattern="*TEMP-aggregated-timeseries_*.nc")

    Parameters
    ----------
    moorings : list
        List of tuples (region, mooring_ID) to load.
    data_type : str
        Data type to load, e.g. "aggregated_timeseries", "hourly_timeseries".
    pattern : str
        Pattern to match the files.
    """
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
            print(f"Downloading {data_type} for mooring '{mooring}'.")
            path = f"s3://imos-data/IMOS/ANMN/{region}/{mooring}/{data_type.replace('-', '_')}/"
            file_url = load_file_urls(path, pattern=f"{pattern}")[0]
            files[mooring] = file_url        
        # Load them locally if they exist
        else:
            print(f"Loading local {data_type} data for mooring '{mooring}'.")
            file_url = glob_path[0]
            files[mooring] = file_url
        
        outdir = Path(f"{data_dir}/{region}/{mooring}/")
        if not outdir.exists():
            Path.mkdir(outdir, parents=True)
        outfile = Path(outdir).joinpath(file_url.split("/")[-1])
        ds[mooring] = open_nc(str(outfile) if local else str(file_url), remote=not local)
        
        # Write files locally if they don't exist
        if not local:
            ds[mooring].to_netcdf(outfile)
    
    return files, ds


def create_modelling_data(mooring_csv):
    """
    Preprocesses the mooring temp series CSV data along with the indexes data.
    """
    dataframes = {}
    dataframes["Upwelling"] = pd.read_csv(mooring_csv)
    dataframes["Upwelling"]["date"] = pd.to_datetime(dataframes["Upwelling"]["TIME"])
    dataframes["Upwelling"] = dataframes["Upwelling"][["TEMP", "DEPTH", "date"]].rename(columns={"TEMP": "Mooring Temp", "DEPTH": "Mooring Depth"})

    files = {
        "SAM": "../Datasets/SAM_index.csv",
        "ENSO": "../Datasets/SOI_index.csv",
        "IOD": "../Datasets/iod_index.csv",
        "Polar_vortex": "../Datasets/Vortex_datasets.csv"
    }

    for k, v in files.items():
        dataframes[k] = pd.read_csv(v)

    for df in "Upwelling SAM ENSO IOD".split():
        dataframes[df]["date"] = pd.to_datetime(dataframes[df]["date"], dayfirst=True)
        dataframes[df]["Year"] = dataframes[df]["date"].dt.year
        dataframes[df]["Month"] = dataframes[df]["date"].dt.to_period("M")
        dataframes[df] = dataframes[df].groupby("Month").mean(numeric_only=True)

    dataframes["Polar_vortex"] = dataframes["Polar_vortex"].dropna().copy()
    dataframes["Polar_vortex"]["Year"] = dataframes["Polar_vortex"]["Year"].astype(int)
    dataframes["Polar_vortex"] = dataframes["Polar_vortex"].set_index("Year")

    data = pd.DataFrame(index=dataframes["Upwelling"].index)
    for k, v in dataframes.items():
        if k != "Polar_vortex":
            data = data.merge(v.drop("Year", axis=1), left_index=True, right_index=True)

    rename_dict = {'Mooring Temp': "Mooring Temp",
                   'Mooring Depth': "Mooring Depth",
                   'sam_index': "SAM",
                   'soi_index': "ENSO",
                   'iod_index': "IOD",
                   'S-Tmode_Lim_et_al_2018': "Polar vortex 1",
                   'Sep-Nov[U]_60S10hPa_JRA55': "Polar vortex 2"}

    data = data.rename(columns=rename_dict)
    data = data.dropna(subset=["Mooring Temp"])
    # Separate features (climatic indices) and target (upwelling) variables
    X = data[['SAM', 'ENSO', 'IOD',]] # 'Polar vortex 1', 'Polar vortex 2']]
    y = data['Mooring Temp']
    
    return data, X, y


def create_regression_model(X, y, test_size=0.35, random_state=42, model=LinearRegression, mooring_id=None):
    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    # Create a linear regression model
    model = model()

    # Train the model on the training data
    model.fit(X_train, y_train)

    # Make predictions on the testing data
    y_pred = model.predict(X_test)

    # Evaluate the model's performance
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("Mean Squared Error:", mse)
    print("R-squared:", r2)

    # Plot the predicted vs. actual upwelling values
    # plt.scatter(y_test, y_pred)
    sns.regplot(x=y_test, y=y_pred)
    plt.xlabel("Actual Upwelling")
    plt.ylabel("Predicted Upwelling")
    title = "Actual vs. Predicted Upwelling"
    if mooring_id:
        title = mooring_id + " " + title
    plt.title(title)
    plt.show()
    
    return model, mse, r2
