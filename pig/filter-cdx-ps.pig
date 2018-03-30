%default INPUT ''
%default OUTPUT ''

set mapreduce.job.queuename default

cdx = LOAD '$INPUT' AS cdxline:chararray;
cdx = FILTER cdx BY not STARTSWITH (cdxline, 'filedesc');
cdx = FILTER cdx BY not STARTSWITH (cdxline, ' ');

cdx = FOREACH cdx GENERATE STRSPLIT(cdxline,'\\s+') as cols, cdxline;
cdx = FOREACH cdx GENERATE (chararray)cols.$0 as url, (chararray)cols.$1 as timestamp, (chararray)cols.$3 as mimetype, (chararray)cols.$4 as httpstatus, cdxline;
cdx = FILTER cdx BY not url matches '-';
cdx = FILTER cdx BY httpstatus matches '200';
cdx = FILTER cdx BY mimetype matches '.*postscript.*';
cdx = ORDER cdx by url, timestamp PARALLEL 50;
cdx = FOREACH cdx GENERATE cdxline;
STORE cdx INTO '$OUTPUT' USING PigStorage(' ');

