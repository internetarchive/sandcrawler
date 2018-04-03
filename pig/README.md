
As of March 2018, the archive runs Pig version 0.12.0, via CDH5.0.1 (Cloudera
Distribution).

"Local mode" unit tests in this folder run with Pig version 0.17.0 (controlled
by `fetch_deps.sh`) due to [dependency/jar issues][pig-bug] in local mode of
0.12.0.

[pig-bug]: https://issues.apache.org/jira/browse/PIG-3530

## Development and Testing

Fetch dependencies (pig):

    ./fetch_deps.sh

Write .pig scripts here, and add a pytho wrapper test to `./tests/` when done.
Test vector files (input/output) can go in `./tests/files/`.

Run the tests with:

    pipenv run pytest

Could also, in theory, use a docker image ([local-pig][]), but it's pretty easy
to just download.

[local-pig]: https://hub.docker.com/r/chalimartines/local-pig

