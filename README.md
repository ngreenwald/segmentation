[![Build Status](https://travis-ci.com/angelolab/ark-analysis.svg?branch=master)](https://travis-ci.com/angelolab/ark-analysis)
[![Coverage Status](https://coveralls.io/repos/github/angelolab/ark-analysis/badge.svg?branch=master)](https://coveralls.io/github/angelolab/ark-analysis?branch=master)

# ark-analysis

Toolbox for analyzing multiplexed imaging data.

Full documentation for the project can be found [here](https://ark-analysis.readthedocs.io/en/latest/).

## Table of Contents
- [Getting Started](#getting-started)
  - [Overview](#overview)
    - [1. Segmentation](#1-segmentation)
    - [2. Pixel clustering with Pixie](#2-pixel-clustering-with-pixie)
    - [3. Cell clustering with Pixie](#3-cell-clustering-with-pixie)
    - [4. Spatial analysis](#4-spatial-analysis)
  - [Installation Steps](#installation-steps)
    - [Download the Repo](#download-the-repo)
    - [Getting the Docker Image](#getting-the-docker-image)
    - [Running on Windows](#running-on-windows)
    - [Using the Repository (Running the Docker)](#using-the-repository-running-the-docker)
- [External Tools](#external-tools)
  - [Mantis Viewer](#mantis-viewer)
  - [External Hard Drives and Google File Stream](#external-hard-drives-and-google-file-stream)
- [Updating the Repository](#updating-the-repository)
- [Questions?](#questions)
- [Want to contribute?](#want-to-contribute)
- [How to Cite](#how-to-cite)

## Getting Started

### Overview
This repo contains tools for analyzing multiplexed imaging data. The assumption is that you've already performed any necessary image processing on your data (such as denoising, background subtraction, autofluorescence correction, etc), and that it is ready to be analyzed. For MIBI data, we recommend using the [toffy](https://github.com/angelolab/toffy) processing pipeline.

#### 1. Segmentation  
The [**segmentation notebook**](./templates_ark/1_Segment_Image_Data.ipynb) will walk you through the process of using [Mesmer](https://www.nature.com/articles/s41587-021-01094-0) to segment your image data. This includes selecting the appropriate channel(s) for segmentation, running your data through the network, and then extracting single-cell statistics from the resulting segmentation mask. 

#### 2. Pixel clustering with Pixie  
The first step in the [Pixie](https://www.biorxiv.org/content/10.1101/2022.08.16.504171v1) pipeline is to run the [**pixel clustering notebook**](./templates_ark/2_Cluster_Pixels.ipynb). The notebook walks you through the process of generating pixel clusters for your data, and lets you specify what markers to use for the clustering, train a model, use it to classify your entire dataset, and generate pixel cluster overlays. The notebook includes a GUI for manual cluster adjustment and annotation.

#### 3. Cell clustering with Pixie  
The second step in the [Pixie](https://www.biorxiv.org/content/10.1101/2022.08.16.504171v1) pipeline is to run the [**cell clustering notebook**](./templates_ark/3_Cluster_Cells.ipynb). This notebook will use the pixel clusters generated in the first notebook to cluster the cells in your dataset. The notebook walks you through generating cell clusters for your data and generates cell cluster overlays. The notebook includes a GUI for manual cluster adjustment and annotation.

#### 4. Spatial analysis  
TBD once notebooks are finished


### Installation Steps

#### Download the Repo

Open terminal and navigate to where you want the code stored. 

Then input the command:

```
git clone https://github.com/angelolab/ark-analysis.git
```

#### Getting the Docker Image

Next, you'll need to set up the Docker image with all of the required dependencies:
 - First, [download](https://hub.docker.com/?overlay=onboarding) Docker Desktop. 
 - Once it's sucessfully installed, make sure it is running by looking in toolbar for the Docker whale icon. 
 - Once it's running, enter the following commands into terminal 

```
cd ark-analysis
docker pull angelolab/ark-analysis:latest
``` 

You can now start to analyze your multiplexed imaging data!


#### Running on Windows

Our repo runs best on Linux-based systems (including MacOS). If you need to run on Windows, please consult our [Windows guide](https://ark-analysis.readthedocs.io/en/latest/_rtd/windows_setup.html) for additional instructions.

#### Using the Repository (Running the Docker)

Enter the following command into terminal from the same directory you ran the above commands:

```
./start_docker.sh
``` 

This will generate a link to a jupyter notebook. Copy the last URL (the one with `127.0.0.1:8888` at the beginning) into your web browser. 

Be sure to keep this terminal open.  **Do not exit the terminal or enter `control-c` until you are finished with the notebooks**. 

**NOTE:**

If you already have a Jupyter session open when you run `./start_docker.sh`, you will receive a couple additional prompts.

Copy the URL listed after `Enter this URL instead to access the notebooks:` 

You will need to authenticate. Note the last URL (the one with `127.0.0.1:8888` at the beginning), copy the token that appears there (it will be after `token=` in the URL), paste it into the password prompt of the Jupyter notebook, and log in.

You can shut down the notebooks and close docker by entering `control-c` in the terminal window.

**REMEMBER TO DUPLICATE AND RENAME NOTEBOOKS**

If you didn't change the name of any of the notebooks within the `templates_ark` folder, they will be overwritten when you decide to update the repo. Read about updating Ark [here](#updating-the-repository)

## External Tools

### Mantis Viewer

We use [Mantis Viewer](https://mantis.parkerici.org) to visualize the segmented images. 
Below you can see the structure of a Mantis project in order to open it in the visualization tool.


Mantis Project Structure:
```sh
mantis_project
├── fov0
│   ├── cell_segmentation.tiff
│   ├── chan0.tiff
│   ├── chan1.tiff
│   ├── chan2.tiff
│   ├── ...
│   ├── population_mask.csv
│   └── population_mask.tiff
└── fov1
│   ├── cell_segmentation.tiff
│   ├── chan0.tiff
│   ├── chan1.tiff
│   ├── chan2.tiff
│   ├── ...
│   ├── population_mask.csv
│   └── population_mask.tiff
└── ...
```

### External Hard Drives and Google File Stream

To configure external hard drive (or google file stream) access, you will have to add this to Dockers file paths in the Preferences menu. 

On Docker for macOS, this can be found in Preferences -> Resources -> File Sharing.  Adding `/Volumes` will allow docker to see external drives 

On Docker for Windows with the WSL2 backend, no paths need to be added.  However, if using the Hyper-V backend, these paths will need to be added as in the macOS case.

![](docs/docker_preferences.png)

Once the path is added, you can run:
```
bash start_docker.sh --external 'path/added/to/preferences'
```
or
```
bash start_docker.sh -e 'path/added/to/preferences'
```

to mount the drive into the virtual `/data/external` path inside the docker.

## Updating the Repository

This project is still under development, and we are making frequent changes and improvements. If you want to update the version on your computer to have the latest changes, perform the following steps. Otherwise, we recommend waiting for new releases.

First, get the latest version of the repository.

```
git pull
```

Check for Docker updates by running:

```
docker pull angelolab/ark-analysis:latest
```

Then, run the command below to update the Jupyter notebooks to the latest version
```
./start_docker.sh --update
```
or
```
./start_docker.sh -u
```

If you have made changes to these notebooks that you would like to keep (specific file paths, settings, custom routines, etc), rename them before updating! 

For example, rename your existing copy of `1_Segment_Image_Data.ipynb` to `1_Segment_Image_Data_old.ipynb`. Then, after running the update command, a new version of `1_Segment_Image_Data.ipynb` will be created with the newest code, and your old copy will exist with the new name that you gave it. 

After updating, you can copy over any important paths or modifications from the old notebooks into the new notebook.

## Questions?

If you run into trouble, please first refer to our [FAQ](https://ark-analysis.readthedocs.io/en/latest/_rtd/faq.html). If that doesn't answer your question, you can open an [issue](https://github.com/angelolab/ark-analysis/issues). Before opening, please double check and see that someone else hasn't opened an issue for your question already. 

## Want to contribute?  

If you would like to help make `ark` better, please take a look at our [contributing guidelines](https://ark-analysis.readthedocs.io/en/latest/_rtd/contributing.html). 

## How to Cite
Please cite the following papers if you found our repo useful!

1. [Greenwald, Miller et al. Whole-cell segmentation of tissue images with human-level performance using large-scale data annotation and deep learning [2021]](https://www.nature.com/articles/s41587-021-01094-0)
2. [Liu, Greenwald et al. Robust phenotyping of highly multiplexed tissue imaging data using pixel-level clustering [2022]](https://www.biorxiv.org/content/10.1101/2022.08.16.504171v1)