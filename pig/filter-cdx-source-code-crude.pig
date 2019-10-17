
-- Tries to filter down a large CDX file (GWB index) to a subset of source code
-- files by mimetype and file extension.
-- This is pretty crude and requires the URL to end with the file extension.
---
-- Author: Bryan Newbold <bnewbold@archive.org>
-- Date: October 2019


%default INPUT ''
%default OUTPUT ''

set mapreduce.job.queuename default

cdx = LOAD '$INPUT' AS cdxline:chararray;
cdx = FILTER cdx BY not STARTSWITH (cdxline, 'filedesc');
cdx = FILTER cdx BY not STARTSWITH (cdxline, ' ');

cdx = FOREACH cdx GENERATE STRSPLIT(cdxline,'\\s+') as cols, cdxline;
cdx = FOREACH cdx GENERATE (chararray)cols.$0 as surt, (chararray)cols.$1 as timestamp, (chararray)cols.$3 as mimetype, (chararray)cols.$4 as httpstatus, (chararray)cols.$5 as sha1sum, cdxline;
cdx = FILTER cdx BY not surt matches '-';
cdx = FILTER cdx BY httpstatus matches '200';
cdx = FILTER cdx BY mimetype matches '.*text.*';

-- This is the core regex
cdx = FILTER cdx

        -- file suffix
        BY surt matches '.*\\).*\\.(c|h|py|java)';

-- DISTINCT by sha1 column
cdx_uniq = FOREACH (GROUP cdx BY sha1sum) {
    r = TOP(1, 0, $1);
    GENERATE FLATTEN(r);
};

cdx_uniq = ORDER cdx_uniq by surt, timestamp PARALLEL 50;
cdx_uniq = FOREACH cdx_uniq GENERATE cdxline;
STORE cdx_uniq INTO '$OUTPUT' USING PigStorage(' ');

