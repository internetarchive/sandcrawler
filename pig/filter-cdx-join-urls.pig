
--
-- Author: Bryan Newbold <bnewbold@archive.org>
-- Date: May 2018

%default INPUT_CDX ''
%default INPUT_URLS ''
%default OUTPUT ''

REGISTER /home/webcrawl/pig-scripts/jars/ia-web-commons-jar-with-dependencies-CDH3.jar;
REGISTER /home/webcrawl/pig-scripts/jars/pigtools.jar;
DEFINE SURTURL pigtools.SurtUrlKey();

set mapreduce.job.queuename default

urls = LOAD '$INPUT_URLS' USING PigStorage() AS url:chararray;
surts = FOREACH urls GENERATE SURTURL(url) AS url_surt;
surts = ORDER surts by url_surt ASC PARALLEL 10;
surts = DISTINCT surts;

cdx = LOAD '$INPUT_CDX' AS cdxline:chararray;
cdx = FILTER cdx BY not STARTSWITH (cdxline, 'filedesc');
cdx = FILTER cdx BY not STARTSWITH (cdxline, ' ');

cdx = FOREACH cdx GENERATE STRSPLIT(cdxline,'\\s+') as cols, cdxline;
cdx = FOREACH cdx GENERATE (chararray)cols.$0 as cdx_surt, (chararray)cols.$1 as timestamp, (chararray)cols.$3 as mimetype, (chararray)cols.$4 as httpstatus, (chararray)cols.$5 as sha1sum, cdxline;
cdx = FILTER cdx BY not cdx_surt matches '-';
cdx = FILTER cdx BY httpstatus matches '200';
cdx = FILTER cdx BY mimetype matches '.*pdf.*';

-- Core JOIN
full_join = JOIN cdx BY cdx_surt, surts BY url_surt;

-- DISTINCT by sha1 column
full_uniq = FOREACH (GROUP full_join BY sha1sum) {
    r = TOP(1, 0, $1);
    GENERATE FLATTEN(r);
};

result = FOREACH full_uniq GENERATE cdxline;
result = DISTINCT result;

STORE result INTO '$OUTPUT' USING PigStorage();
