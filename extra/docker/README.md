
The docker-compose script in this directory may be helpful for local
development. It starts Kafka, postgrest, and zookeeper.

PostgreSQL is assumed to be running natively on localhost, not under docker. It
should be possible to add postgresql to the docker-compose file, but some
developers (bnewbold) prefer to run it separately to make things like attaching
with `psql` easier.

There is no current motivation or plan to deploy sandcrawler services using
docker, so there is no Dockerfile for the system itself.
