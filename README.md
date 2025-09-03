![](images/banner.png)

# Onyx

## Overview

Onyx is a Django-based API for managing metadata records, analyses, and other associated data. It provides a flexible system for handling projects with different metadata requirements, and has built-in access control, data validation, sensitive identifier anonymisation, and a granular query system.

## Projects

As part of [CLIMB-TRE](https://climb-tre.github.io/), Onyx serves as the central metadata repository for the following projects:

- [mSCAPE](https://mscape.climb.ac.uk/) (Metagenomics Surveillance Collaboration and Analysis Programme): A collaborative initiative led by UKHSA, involving a consortium of NHS and academic partners, to deliver a pilot surveillance network trialling the use of metagenomic data for public health surveillance and pathogen analysis.
- [PATH-SAFE](https://www.food.gov.uk/our-work/pathogen-surveillance-in-agriculture-food-and-environment-path-safe-programme) (Pathogen Surveillance in Agriculture, Food and Environment): Led by the FSA, PATH-SAFE piloted the development of a national surveillance network to improve the detection and tracking of foodborne human pathogens and AMR within agriculture.
- [synthSCAPE](https://climb-tre.github.io/synthscape/) (Synthetic dataset for mSCAPE)
- [openMGS](https://climb-tre.github.io/openmgs/) (Open Meta-Genomic Surveillance)

## Structure

Different pieces of Onyx (the backend, project definitions and frontend apps) are defined in the following repositories: 

| Repository | Description |
| - | - |
|[onyx](https://github.com/CLIMB-TRE/onyx) | Backend API and database for Onyx. |
| [onyx-client](https://github.com/CLIMB-TRE/onyx-client) | Command-line interface and Python API for interacting with Onyx. |
| [onyx-gui](https://github.com/CLIMB-TRE/onyx-gui) | Graphical user interface for browsing Onyx records/analyses, and producing graphs of aggregated data. |
| [onyx-extension](https://github.com/CLIMB-TRE/onyx-extension) | Wraps the interface provided by [onyx-gui](https://github.com/CLIMB-TRE/onyx-gui) and provides additional logic to convert it into a [JupyterLab extension](https://jupyterlab.readthedocs.io/en/4.4.x/user/extensions.html), making it accessible from [CLIMB Jupyter notebook servers](https://docs.climb.ac.uk/notebook-servers/). |
| onyx-projects (private) | Contains the Django apps that define each active project in CLIMB-TRE, as well as configurations for sites and which projects they have access to. |

## Documentation

Documentation can be found [here](https://climb-tre.github.io/onyx/).
