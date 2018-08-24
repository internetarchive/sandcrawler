#!/usr/bin/env bash

# This script was originally only for pig scripts; now it can also be used to
# run scalding code locally (via please)

set -euo pipefail

#PIG_VERSION="0.12.0-cdh5.2.0"
# Using more recent version to work around snappy classpath problem
PIG_VERSION="0.17.0"
HADOOP_VERSION="2.3.0-cdh5.0.1"

mkdir -p pig/deps/
cd pig/deps/

# Fetch Hadoop Command
echo https://archive.cloudera.com/cdh5/cdh/5/hadoop-${HADOOP_VERSION}.tar.gz
#wget -c https://archive.cloudera.com/cdh5/cdh/5/pig-${HADOOP_VERSION}.tar.gz
#wget -c https://archive.cloudera.com/cdh5/cdh/5/pig-${HADOOP_VERSION}.tar.gz
wget -c https://archive.org/serve/hadoop_pig_mirror/hadoop-${HADOOP_VERSION}.tar.gz
echo "Extracting Hadoop (takes a minute)..."
tar xvf hadoop-${HADOOP_VERSION}.tar.gz > /dev/null
ln -fs hadoop-${HADOOP_VERSION} hadoop

# Fetch Pig
#wget -c https://archive.cloudera.com/cdh5/cdh/5/pig-${PIG_VERSION}.tar.gz
#wget -c http://mirror.metrocast.net/apache/pig/pig-${PIG_VERSION}/pig-${PIG_VERSION}.tar.gz
wget -c https://archive.org/serve/hadoop_pig_mirror/pig-${PIG_VERSION}.tar.gz
echo "Extracting Pig (takes a minute)..."
tar xvf pig-${PIG_VERSION}.tar.gz > /dev/null
ln -fs pig-${PIG_VERSION} pig

# No 'readlink -f' on macOS
# https://stackoverflow.com/a/24572274/4682349
JAVA_HOME=$(perl -MCwd -e 'print Cwd::abs_path shift' /usr/bin/java | sed "s:bin/java::")
./pig/bin/pig -x local -version
./hadoop/bin/hadoop version

