
File Ingest Mode: 'src'
=======================

Ingest type for "source" of works in document form. For example, tarballs of
LaTeX source and figures, as published on arxiv.org and Pubmed Central.

For now, presumption is that this would be a single file (`file` entity in
fatcat).

Initial mimetypes to allow:

- text/x-tex
- application/xml
- application/gzip
- application/x-bzip
- application/x-bzip2
- application/zip
- application/x-tar
- application/msword
- application/vnd.openxmlformats-officedocument.wordprocessingml.document


## Fatcat Changes

In the file importer, allow the additional mimetypes for 'src' ingest.

Might keep ingest disabled on the fatcat side, at least initially. Eg, until
there is some scope of "file scope", or other ways of treating 'src' tarballs
separate from PDFs or other fulltext formats.


## Ingest Changes

Allow additional terminal mimetypes for 'src' crawls.


## Examples

    arxiv:2109.00954v1
    fatcat:release_akzp2lgqjbcbhpoeoitsj5k5hy
    https://arxiv.org/format/2109.00954v1
    https://arxiv.org/e-print/2109.00954v1

    arxiv:1912.03397v2
    https://arxiv.org/format/1912.03397v2
    https://arxiv.org/e-print/1912.03397v2
    NOT: https://arxiv.org/pdf/1912.03397v2

    pmcid:PMC3767916
    https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/08/03/PMC3767916.tar.gz

For PMC, will need to use one of the .csv file lists to get the digit prefixes.
