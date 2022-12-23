
api docs: https://datadryad.org/api/v2/docs

current search queries return 38,000 hits (December 2020)

exmaple with multiple versions:
    https://datadryad.org/stash/dataset/doi:10.5061/dryad.fbg79cnr0
    https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.fbg79cnr0
    https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.fbg79cnr0/versions


how to handle versions? DOI doesn't get incremented.

on archive.org, could have separate item for each version, or sub-directories within item, one for each version

in fatcat, could have a release for each version, but only one with
the DOI; or could have a separate fileset for each version
