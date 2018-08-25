
Commands can be run from any cluster machine with hadoop environment config
set up. Most of these commands are run from the shell (start with `hbase
shell`). There is only one AIT/Webgroup HBase instance/namespace; there may be
QA/prod tables, but there are not QA/prod clusters.

## Create Table

Create column families (note: not all individual columns) with something like:

    create 'wbgrp-journal-extract-0-qa', 'f', 'file', {NAME => 'grobid0', COMPRESSION => 'snappy'}

## Run Thrift Server Informally

The Thrift server can technically be run from any old cluster machine that has
Hadoop client stuff set up, using:

    hbase thrift start -nonblocking -c

Note that this will run version 0.96, while the actual HBase service seems to
be running 0.98.

To interact with this config, use happybase (python) config:

    conn = happybase.Connection("bnewbold-dev.us.archive.org", transport="framed", protocol="compact")
    # Test connection
    conn.tables()

## Queries From Shell

Fetch all columns for a single row:

    hbase> get 'wbgrp-journal-extract-0-qa', 'sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ'

Fetch multiple columns for a single row, using column families:

    hbase> get 'wbgrp-journal-extract-0-qa', 'sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ', 'f', 'file'

Scan a fixed number of rows (here 5) starting at a specific key prefix, all
columns:

    hbase> scan 'wbgrp-journal-extract-0-qa',{LIMIT=>5,STARTROW=>'sha1:A'}
