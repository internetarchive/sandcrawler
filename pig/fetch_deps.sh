#!/usr/bin/env bash

set -euo pipefail

#PIG_VERSION="0.12.0-cdh5.2.0"
# Using more recent version to work around snappy classpath problem
PIG_VERSION="0.17.0"
JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:bin/java::")

mkdir -p deps/
cd deps/

# Fetch Pig
#wget -c https://archive.cloudera.com/cdh5/cdh/5/pig-${PIG_VERSION}.tar.gz
#wget -c http://mirror.metrocast.net/apache/pig/pig-${PIG_VERSION}/pig-${PIG_VERSION}.tar.gz
wget -c https://archive.org/serve/hadoop_pig_mirror/pig-${PIG_VERSION}.tar.gz
tar xvf pig-${PIG_VERSION}.tar.gz
ln -fs pig-${PIG_VERSION} pig
./pig/bin/pig -x local -version

