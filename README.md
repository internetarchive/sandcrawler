
                                     _                         _           
    __________    ___  __ _ _ __   __| | ___ _ __ __ ___      _| | ___ _ __ 
    \         |  / __|/ _` | '_ \ / _` |/ __| '__/ _` \ \ /\ / / |/ _ \ '__|
     \        |  \__ \ (_| | | | | (_| | (__| | | (_| |\ V  V /| |  __/ |   
      \ooooooo|  |___/\__,_|_| |_|\__,_|\___|_|  \__,_| \_/\_/ |_|\___|_|   


This repo contains hadoop tasks (mapreduce and pig), luigi jobs, and other
scripts and code for the internet archive (web group) journal ingest pipeline.

This repository is potentially public.

Archive-specific deployment/production guides and ansible scripts at:
[journal-infra](https://git.archive.org/bnewbold/journal-infra)

## Python Setup

Pretty much everything here uses python/pipenv. To setup your environment for
this, and python in general:

    # libjpeg-dev is for some wayback/pillow stuff
    sudo apt install python3-dev python3-pip python3-wheel libjpeg-dev
    pip3 install --user pipenv
