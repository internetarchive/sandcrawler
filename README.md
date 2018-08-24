
                                      _                         _           
    __________    ___  __ _ _ __   __| | ___ _ __ __ ___      _| | ___ _ __ 
    \         |  / __|/ _` | '_ \ / _` |/ __| '__/ _` \ \ /\ / / |/ _ \ '__|
     \        |  \__ \ (_| | | | | (_| | (__| | | (_| |\ V  V /| |  __/ |   
      \ooooooo|  |___/\__,_|_| |_|\__,_|\___|_|  \__,_| \_/\_/ |_|\___|_|   


This repo contains hadoop jobs, luigi tasks, and other scripts and code for the
internet archive web group's journal ingest pipeline.

Code in tihs repository is potentially public!

Archive-specific deployment/production guides and ansible scripts at:
[journal-infra](https://git.archive.org/bnewbold/journal-infra)

**./python/** contains Hadoop streaming jobs written in python using the
`mrjob` library. Most notably, the **extraction** scripts, which fetch PDF
files from wayback/petabox, process them with GROBID, and store the result in
HBase.

**./scalding/** contains Hadoop jobs written in Scala using the Scalding
framework. The intent is to write new non-trivial Hadoop jobs in Scala, which
brings type safety and compiled performance.

**./pig/** contains a handful of Pig scripts, as well as some unittests
implemented in python.

## Running Hadoop Jobs

The `./please` python3 wrapper script is a helper for running jobs (python or
scalding) on the IA Hadoop cluster. You'll need to run the setup/dependency
tasks first; see README files in subdirectories.

