
File Ingest Mode: 'component'
=============================

A new ingest type for downloading individual files which are a subset of a
complete work.

Some publishers now assign DOIs to individual figures, supplements, and other
"components" of an over release or document.

Initial mimetypes to allow:

- image/jpeg
- image/tiff
- image/png
- image/gif
- audio/mpeg
- video/mp4
- video/mpeg
- text/plain
- text/csv
- application/json
- application/xml
- application/pdf
- application/gzip
- application/x-bzip
- application/x-bzip2
- application/zip
- application/x-rar
- application/x-7z-compressed
- application/x-tar
- application/vnd.ms-powerpoint
- application/vnd.ms-excel
- application/msword
- application/vnd.openxmlformats-officedocument.wordprocessingml.document
- application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

Intentionally not supporting:

- text/html


## Fatcat Changes

In the file importer, allow the additional mimetypes for 'component' ingest.


## Ingest Changes

Allow additional terminal mimetypes for 'component' crawls.


## Examples

Hundreds of thousands: <https://fatcat.wiki/release/search?q=type%3Acomponent+in_ia%3Afalse>

#### ACS Supplement File

<https://doi.org/10.1021/acscatal.0c02627.s002>

Redirects directly to .zip in browser. SPN is blocked by cookie check.

#### Frontiers .docx Supplement

<https://doi.org/10.3389/fpls.2019.01642.s001>

Redirects to full article page. There is a pop-up for figshare, seems hard to process.

#### Figshare Single FIle

<https://doi.org/10.6084/m9.figshare.13646972.v1>

As 'component' type in fatcat.

Redirects to a landing page. Dataset ingest seems more appropriate for this entire domain.

#### PeerJ supplement file

<https://doi.org/10.7717/peerj.10257/supp-7>

PeerJ is hard because it redirects to a single HTML page, which has links to
supplements in the HTML. Perhaps a custom extractor will work.

#### eLife

<https://doi.org/10.7554/elife.38407.010>

The current crawl mechanism makes it seemingly impossible to extract a specific
supplement from the document as a whole.

#### Zookeys

<https://doi.org/10.3897/zookeys.895.38576.figure53>

These are extract-able.

#### OECD PDF Supplement

<https://doi.org/10.1787/f08c6324-en>
<https://www.oecd-ilibrary.org/trade/imports-of-services-billions-of-us-dollars_f08c6324-en>

Has an Excel (.xls) link, great, but then paywall.

#### Direct File Link

<https://doi.org/10.1787/888934207500>

This one is also OECD, but is a simple direct download.

#### Protein Data Base (PDB) Entry

<https://doi.org/10.2210/pdb6ls2/pdb>

Multiple files; dataset/fileset more appropriate for these.
