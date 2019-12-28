
--
-- Author: Bryan Newbold <bnewbold@archive.org>
-- Date: December 2020
--
-- This pig script is intended to run agains the full (many TByte) GWB CDX, and
-- catch captures that match exact SHA1 (b32 encoded), regardless of mimetype.
--
-- The process is to filter the CDX for non-revisit HTTP 200s, sort this by
-- SHA1 digest, then join with the (pre-sorted) SHA1 -- b32 input list, and dump
-- output.

%default INPUT_CDX ''
%default INPUT_DIGEST ''
%default OUTPUT ''

set mapreduce.job.queuename default

digests = LOAD '$INPUT_DIGEST' AS sha1b32:chararray;
digests = ORDER digests by sha1b32 ASC PARALLEL 20;
digests = DISTINCT digests;

cdx = LOAD '$INPUT_CDX' AS cdxline:chararray;
cdx = FILTER cdx BY not STARTSWITH (cdxline, 'filedesc');
cdx = FILTER cdx BY not STARTSWITH (cdxline, ' ');

cdx = FOREACH cdx GENERATE STRSPLIT(cdxline,'\\s+') as cols, cdxline;
cdx = FOREACH cdx GENERATE (chararray)cols.$0 as cdx_surt, (chararray)cols.$1 as timestamp, (chararray)cols.$3 as mimetype, (chararray)cols.$4 as httpstatus, (chararray)cols.$5 as sha1b32, cdxline;
cdx = FILTER cdx BY not cdx_surt matches '-';
cdx = FILTER cdx BY httpstatus matches '200';
cdx = FILTER cdx BY not mimetype matches 'warc/revisit';
cdx = ORDER cdx BY sha1b32 ASC PARALLEL 40;

-- TODO: DISTINCT by (sha1b32, cdx_surt) for efficiency

-- Core JOIN
full_join = JOIN cdx BY sha1b32, digests BY sha1b32;

-- TODO: at most, say 5 CDX lines per sha1b32?

result = FOREACH full_join GENERATE cdxline;

STORE result INTO '$OUTPUT' USING PigStorage();
