
REGISTER /usr/lib/hbase/hbase-client-0.98.6-cdh5.3.1.jar
REGISTER /usr/lib/hbase/hbase-common-0.98.6-cdh5.3.1.jar

set hbase.zookeeper.quorum 'mtrcs-zk1.us.archive.org,mtrcs-zk2.us.archive.org,mtrcs-zk3.us.archive.org'

data = LOAD 'hbase://wbgrp-journal-extract-0-qa'
       USING org.apache.pig.backend.hadoop.hbase.HBaseStorage('grobid0:status_code', '-loadKey true')
       AS (key:CHARARRAY, status:CHARARRAY);

data_group = GROUP data ALL;
data_count = FOREACH data_group GENERATE COUNT(data);
DUMP data_count;
