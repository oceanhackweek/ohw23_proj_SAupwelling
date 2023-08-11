# ohw23_proj_SAupwelling

Playing with the IMOS data in the past Ocean Hack, I noticed a suppression of the South Australian upwelling on the SA NRS mooring that lead to this question:
What is the variability of the South Australian upwelling and what is driving it?

My idea for this project is to revisit the efforts from the OceanHack 2022 and create a very general “detection and attribution” project. We can tweak it as we go, depending on where our interest takes us. I propose this: 

~~Issue 1: Subset the data from SA moorings.~~ 
  - ~~Create code where we can access the different moorings.~~
  - ~~Create a map where we can see the SA moorings locations with a bathymetry background.~~ 

Issue 2: What is the variability of the South Australia upwelling? 
  - Temperature and salinity anomalies from all moorings. 
  - Climatology (I have the example code for that from past year which would go in here to help.)
  - Process the time series to remove seasonality and check for trends (rolling mean, detrending, subtracting climatology, filtering). 

Issue 3: What is the relationship of this variability with the relevant climate mode for the region? What is the relationship of the variability of the Bonney Coast and stratospheric warming?
  - ~~Load SAM, ENSO indexes.~~ 
  - ~~Create or download an index for stratospheric warming.~~ 
  - Apply statistical methods to analyse the observational data and assess the relationship between the observed changes and the potential drivers. This can involve time-series analysis, correlation analysis, regression modelling, or other statistical techniques.

If we are amazing and got this far: 

~~Issue 4: Develop climate model simulations.~~
  ~~- Use climate models (e.g., global climate models or regional climate models) to simulate the Bonney Coast climate and environmental conditions. Run simulations that include different scenarios or forcings, such as natural variability and anthropogenic forcing, to compare against the observed data.~~

~~Issue 5: Quantify the contributions of different drivers to the observed changes using established attribution methods, such as fingerprinting techniques or attribution frameworks.~~ 

Housekeeping: 
- I have created some issues to help us quickstart the project, but feel free to investigate the data as you please - just comment it through!
- Create and store code on the "Notebooks" folder and, once an issue is resolved, comment the link of the final code and close the issue.

Useful links: 
- IMOS bucket for SA coastal mooring data: http://imos-data.s3-website-ap-southeast-2.amazonaws.com/?prefix=IMOS/ANMN/SA/
- IMOS bucket for SA NRS station data: http://imos-data.s3-website-ap-southeast-2.amazonaws.com/?prefix=IMOS/ANMN/NRS/NRSKAI/
- SA coastal moorings and NRS station technical summary, where you can find the code names for active and deactivated moorings which are important to download the data from the IMOS bucket: https://imos.org.au/facilities/nationalmooringnetwork/samoorings
- AODN portal: https://portal.aodn.org.au/search 

## Installation

You can install the project requirements that are listed in the `environment.yaml` file by running this command:

```bash
conda env create -f environment.yaml
```

You can replace `conda` with `mamba`, if you have it installed.

