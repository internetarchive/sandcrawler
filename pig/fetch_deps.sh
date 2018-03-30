#!/usr/bin/env bash

set -euo pipefail

# If you change this, also update tests/pighelper.py
PIG_VERSION="0.12.0-cdh5.0.1"

mkdir -p deps/
cd deps/
wget -c https://archive.cloudera.com/cdh5/cdh/5/pig-${PIG_VERSION}.tar.gz
tar xvf pig-${PIG_VERSION}.tar.gz
ln -fs pig-${PIG_VERSION} pig
cd pig
ln -fs pig-${PIG_VERSION}.jar pig.jar
cd ..

JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:bin/java::")
./pig/bin/pig -x local -version

