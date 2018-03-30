
As of March 2018, the archive runs Pig version 0.12.0, via CDH5.0.1 (Cloudera
Distribution).

## Development and Testing

To run pig in development on your laptop, you can either use docker or 

https://hub.docker.com/r/chalimartines/local-pig

    wget https://archive.cloudera.com/cdh5/cdh/5/pig-0.12.0-cdh5.0.1.tar.gz
    tar xvf pig-*.tar.gz
    ln -s pig-0.12.0-cdh5.0.1/pig-0.12.0-cdh5.0.1.jar pig-0.12.0-cdh5.0.1/pig.jar
    ./pig-*/bin/pig -x local -version

    #XXX: don't need Hadoop?
    #wget https://archive.cloudera.com/cdh5/cdh/5/hadoop-2.3.0-cdh5.0.1.tar.gz
    #tar xvf hadoop-*.tar.gz
    #export HADOOP_HOME=hadoop-2.3*

Tests require python3, nosetests3, and pigpy. You can install these with:

    pip install pipenv
    pipenv install --three

Then:

    pipenv run nosetests3
