
Find all the PDFs from web which resulted in `bad-grobid-xml` status code (among others):

    sql> select * from grobid where status != 'success' and status_code != 500 and status_code != 503 and status != 'error-timeout' limit 100;

                     sha1hex                  |            updated            | grobid_version | status_code |     status     | fatcat_release |                                metadata
    ------------------------------------------+-------------------------------+----------------+-------------+----------------+----------------+------------------------------------------------------------------------
     d994efeea3b653e2dbe8e13e5a6d203e9b9484ab | 2020-03-20 04:04:40.093094+00 |                |         200 | error          |                | {"error_msg": "response XML too large: 12052192 bytes"}
     8dadf846488ddc2ff3934dd6beee0e3046fa3800 | 2020-11-24 01:24:02.668692+00 |                |         200 | error          |                | {"error_msg": "response XML too large: 18758248 bytes"}
     227900724e5cf9fbd06146c914239d0c12c3671a | 2020-03-18 10:24:33.394339+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 40, column 1122"}
        https://web.archive.org/web/20200210041053/https://pdfs.semanticscholar.org/2279/00724e5cf9fbd06146c914239d0c12c3671a.pdf
        FIXED
     f667b4ef2befb227078169ed57ffc6efc5fa85c2 | 2020-03-20 04:54:18.902756+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 28, column 527"}
        https://web.archive.org/web/20200218182411/https://pdfs.semanticscholar.org/f667/b4ef2befb227078169ed57ffc6efc5fa85c2.pdf
        FIXED
     c1e8d9df347b8de53fc2116615b1343ba327040d | 2020-11-08 21:46:04.552442+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "mismatched tag: line 198, column 3"}
        https://web.archive.org/web/20200904163312/https://arxiv.org/pdf/1906.02107v1.pdf
        FIXED (and good)
     4d9860a5eeee6bc671c3be859ca78f89669427f0 | 2021-11-04 01:29:13.081596+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "unclosed token: line 812, column 7"}
        https://web.archive.org/web/20211104012833/https://actabalneologica.eu/wp-content/uploads/library/ActaBalneol2021i3.pdf
        FIXED
        metadata quality mixed, but complex document (?)
     7cfc0739be9c49d94272110a0a748256bdde9be6 | 2021-07-25 17:06:03.919073+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 38, column 440"}
        https://web.archive.org/web/20210716124436/https://jsesd.csers-ly.com/index.php/jsesd/article/download/28/23
        FIXED
     088c61a229084d13f85524efcc9f38a80dd19caf | 2021-09-01 08:08:18.531533+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 47, column 814"}
        https://web.archive.org/web/20210814181328/https://wmrj.areeo.ac.ir/article_120843_3806466cb1f5a125c328f99866751a43.pdf
        FIXED
     19e70297e523e9f32cd4379af33a12ab95c34a71 | 2021-11-05 10:09:25.407657+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 853, column 84"}
        not found
     acc855d74431537b98de5185e065e4eacbab7b26 | 2021-11-12 22:57:22.439007+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 60, column 45"}
        https://web.archive.org/web/20211111182756/https://arxiv.org/pdf/2006.13365v5.pdf
        BROKEN: not well-formed (invalid token): line 60, column 45
            <note type="raw_affiliation"><label>&</label> Fraunhofer IAIS, Sankt Augustin and Dresden, Germany.</note>
     8e73055c63d1e684b59059ac418f55690a2eec01 | 2021-11-12 17:34:46.343685+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 44, column 45"}
        not found
     c2b3f696e97b9e80f38c35aa282416e95d6d9f5e | 2021-11-12 22:57:12.417191+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 58, column 45"}
        https://web.archive.org/web/20211112051714/https://ccsenet.org/journal/index.php/gjhs/article/download/0/0/46244/49308
        BROKEN: not well-formed (invalid token): line 58, column 45
            <note type="raw_affiliation"><label>&</label> Ren, 2020; Meng, Hua, &amp; Bian, 2020).</note>
     840d4609308c4a7748393181fe1f6a45f9d425c5 | 2021-11-12 22:57:17.433022+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 1824, column 45"}
        not found
     3deb6375e894c5007207502bf52d751a47a20725 | 2021-11-12 23:11:17.711948+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 65, column 45"}
        not found
     f1d06080a4b1ac72ab75226e692e8737667c29a7 | 2020-01-16 09:23:27.579995+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 29, column 1581"}
        https://web.archive.org/web/20180721030918/https://journals.squ.edu.om/index.php/jams/article/download/650/649
        FIXED, good
     f3e7b91fce9132addc59bd1560c5eb16c0330842 | 2020-01-12 11:58:06.654613+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 40, column 1122"}
        https://web.archive.org/web/20180426020051/http://jhsw.tums.ac.ir/article-1-5121-en.pdf
        FIXED
     37edcaa6f67fbb8c3e27fa02da4f0fa780e33bca | 2020-01-04 21:53:49.578847+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 28, column 1284"}
        https://web.archive.org/web/20180510115632/http://www.fmreview.org/sites/fmr/files/FMRdownloads/ar/detention/majidi.pdf
        FIXED
     3f1d302143824808f7109032687a327708896748 | 2020-01-05 20:51:18.783034+00 |                |         200 | bad-grobid-xml |                | {"error_msg": "not well-formed (invalid token): line 40, column 1122"}
        https://web.archive.org/web/20180428082655/http://jhsw.tums.ac.ir/browse.php?a_id=5121&sid=1&slc_lang=fa&ftxt=1
        FIXED
    (21 rows)

Some other errors from other queries:

     d9634f194bc3dee27db7a1cb49b30e48803d7ad8 | 2020-01-06 16:01:09.331272+00 |                |         500 | error  |                | {"error_msg": "[PARSING_ERROR] Cannot parse file: /run/grobid/tmp/VyuJWqREHT.lxml"}
        https://web.archive.org/web/20190304092121/http://pdfs.semanticscholar.org/d963/4f194bc3dee27db7a1cb49b30e48803d7ad8.pdf
        FIXED: with 0.7.0+

     56c9b5398ef94df54d699342740956caf4523925 | 2020-02-06 21:37:42.139761+00 |                |         500 | error  |                | {"error_msg": "[BAD_INPUT_DATA] PDF to XML conversion failed with error code: 1"}
        https://web.archive.org/web/20080907000756/http://www.rpi.edu/~limc/poster_ding.pdf
        still errors: "error_msg": "[BAD_INPUT_DATA] PDF to XML conversion failed with error code: 1", "status": "error", "status_code": 500
        BAD PDF ("no pages" in evince)

     d7cf65ed211cf1e3420c595fdbecc5d18f297b11 | 2020-01-10 23:19:16.783415+00 |                |         500 | error  |                | {"error_msg": "[PARSING_ERROR] Cannot parse file: /run/grobid/tmp/dBV73X4HrZ.lxml"}
        https://web.archive.org/web/20170812074846/http://dspace.utpl.edu.ec/bitstream/123456789/7918/1/Tesis_de_Jacome_Valdivieso_Soraya_Stephan%c3%ada.pdf
        FIXED

     51d070ab398a8744286ef7356445f0828a9f3abb | 2020-02-06 16:01:23.98892+00  |                |         503 | error  |                | {"error_msg": "<html>\n<head>\n<meta http-equiv=\"Content-Type\" content=\"text/html;charset=utf-8\"/>\n<t
        https://web.archive.org/web/20191113160818/http://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC2082155&blobtype=pdf
        FIXED

In summary, there are still a small number of `bad-grobid-xml` cases, and still
many "very large PDF" cases. But we should probably broadly retry everything,
especially the 503 errors (from when GROBID is simply down/unavailable).

The `bad-grobid-xml` cases here were all from "<label>" in raw affiliations,
which I have submitted a patch/PR for.
