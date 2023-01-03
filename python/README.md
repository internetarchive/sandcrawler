
This directory contains `sandcrawler` python code for ingest pipelines, batch
processing, PDF extraction, etc.


## Development Quickstart

As of December 2022, working with this code requires:

- Python 3.8 (specifically, due to version specification in `pipenv`)
- `pipenv` for python dependency management
- generic and python-specific build tools (`pkg-config`, `python-dev`, etc)
- poppler (PDF processing library)
- libmagic
- libsodium
- access to IA internal packages (`devpi.us.archive.org`), specifically for
  globalwayback and related packages

In production and CI we use Ubuntu Focal (20.04). The CI script for this
repository (`../.gitlab-ci.yml`) is the best place to look for a complete list
of dependencies for both development and deployment. Note that our CI system
runs from our cluster, which resolves the devpi access issue. For developer
laptops, you may need `sshuttle` or something similar set up to do initial
package pulls.

It is recommended to set the env variable `PIPENV_VENV_IN_PROJECT=true` when
working with pipenv. You can include this in a `.env` file.

There is a Makefile which helps with the basics. Eg:

    # install deps using pipenv
    make deps

    # run python tests
    make test

    # run code formatting and lint checks
    make fmt lint

Sometimes when developing it is helpful to enter a shell with pipenv, eg:

    pipenv shell

Often when developing it is helpful (or necessary) to set environment
variables. `pipenv shell` will read from `.env`, so you can copy and edit
`example.env`, and it will be used in tests, `pipenv shell`, etc.
