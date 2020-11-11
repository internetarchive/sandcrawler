
## Current Plan

- selectolax to extract metadata and quickly filter (speed)
    => eg, differentiate landing pages from fulltext
    => also embed URLs?
- trafilatura for fulltext body extract
- no solution yet for reference parsing
    => maybe trafilatura XML-TEI parsing, then GROBID?
    => especially if DOI/identifier/URL is in the reference



TODO:
x print/wrap error condition better
x serialize dates (pydantic)
x CDX lookup "closest" to capture datetime (or by month)
x firstmonday no extracted fulltext/XML
x apply URL base fixup to fulltext URLs
x XML alternative detection
- basic ingest worker, kafka topics, persist workers, sql table, etc
- ingest worker: landing page to actual fulltext (eg, OJS)
- broken? https://betterexplained.com/articles/colorized-math-equations/

Ponder:
- CDX lookup older successful captures
    http://www.altdevblogaday.com/2011/05/17/understanding-the-fourier-transform/
    => optional filter by status? "reduce" by month/year?
- detect scope heuristically
    bepress_is_article_cover_page 1
    citation_fulltext_world_readable "" (eg, distill)
- non-success subresource fetches
    https://www.europenowjournal.org/2020/10/11/a-social-history-of-early-rock-n-roll-in-germany-hamburg-from-burlesque-to-the-beatles-1956-1969/
- redirects: keep start URL?

Later:
- XML URL extraction
    https://www.scielo.br/scielo.php?script=sci_arttext&pid=S0100-19652002000200001&lng=en&nrm=iso&tlng=pt
    <a href="http://www.scielo.br/scieloOrg/php/articleXML.php?pid=S0100-19652002000200001&amp;lang=en" rel="nofollow" target="xml">
- selectolax bug?  hangs: `css_first("meta['thing']")`
- youtube embed
    => download/include actual video file?
- parse references in citation headers
- try parsing references in HTML fulltext

## Testing URLs

- PLOS
    https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0093949
    TODO: "May 9, 2014"
    TODO: appendix
- peerj
    https://peerj.com/articles/4375/
- scielo
    http://scielo.iics.una.py/scielo.php?script=sci_arttext&pid=S1683-98032020000200081&lng=en&nrm=iso&tlng=es
    bunch of little icon .png, but ok
    redirect of an image not saved in webcapture
- wordpress
    https://www.europenowjournal.org/2020/10/11/a-social-history-of-early-rock-n-roll-in-germany-hamburg-from-burlesque-to-the-beatles-1956-1969/
        no HTML meta? hrm
- old OJS
    (pdf only) http://rjh.folium.ru/index.php/rjh/article/view/1511
- new OJS
    https://firstmonday.org/ojs/index.php/fm/article/view/10274/9729
- plain HTML
    http://journal.sjdm.org/12/12627/jdm12627.html
- blogs/essays
    http://symbolflux.com/lodessay/
    https://betterexplained.com/articles/colorized-math-equations/
    https://web.archive.org/web/20120418231513/http://www.altdevblogaday.com/2011/05/17/understanding-the-fourier-transform/
    https://research.google.com/bigpicture/attacking-discrimination-in-ml/
    http://www.econgraphs.org/
- journal homepage (not fulltext)
- OJS new landing page (not fulltext)
- OJS old (not fulltext)
    http://rjh.folium.ru/index.php/rjh/index
    http://rjh.folium.ru/index.php/rjh/issue/view/106
    http://rjh.folium.ru/index.php/rjh/article/view/382
- distill
    https://distill.pub/2020/bayesian-optimization/
    https://distill.pub/2018/feature-wise-transformations/
- youtube video embed
    http://www.cond.org/persalog.html
- youtube video direct?
- github: project README?
- wikipedia

## Background Research

- scrapy (?)
- requests-html: can run javascript
    => good for metadata extraction?
- selectolax
- scrapely: give HTML and extracted text, it builds the parser
    => good for difficult one-off cases?
- https://rushter.com/blog/python-fast-html-parser/
- WET generation from WARC, a la common crawl
- https://towardsdatascience.com/categorizing-world-wide-web-c130abd9b717

Other random stuff:
- distilBERT: most BERT accuracy, 0.4 factor latency (faster)?
    https://medium.com/huggingface/distilbert-8cf3380435b5
- htmldate: finds "date of publication" for a document
- adblockparser
    => good as a filter in HTML ingest
- w3lib: utility library. unicode conversion; cleanups; etc
- courlan: clean/normalize/sample large URL lists
    => https://github.com/adbar/courlan

### Main Text Extraction

Things to try:

- newspaper3k
    => basic article extraction. lxml
- trafilatura
    => TEI-XML output!
    => looks very promising
    => falls back to readability and justext
- python-readability
    => improved vs newspaper?
- dragnet
- eatiht
- jusText
- inscriptis
    => emphasis on shape/readability of text output? compare with lynx
- Goose3
    => metadata and article text
- news-please
    => very full-featured. build on scrapy, newspaper, readability
    => can iterate over common crawl?
- html2text
    => actually HTML-to-markdown; no or little "boilerplate removal"
- boilerpipe (Java)
    boilerpipe3 (wrapper)
    boilerpy3 (port)

Comparisons and articles: 

- https://www.diffbot.com/benefits/comparison/
- https://github.com/scrapinghub/article-extraction-benchmark
  - https://github.com/scrapinghub/article-extraction-benchmark/releases/download/v1.0.0/paper-v1.0.0.pdf
- https://github.com/rundimeco/waddle

- https://moz.com/devblog/benchmarking-python-content-extraction-algorithms-dragnet-readability-goose-and-eatiht
- https://hal.archives-ouvertes.fr/hal-02768510v3/document (fr; June 2020)
    https://translate.google.com/translate?sl=auto&tl=en&u=https%3A%2F%2Fhal.archives-ouvertes.fr%2Fhal-02768510v3%2Fdocument
- http://eprints.fri.uni-lj.si/1718/1/Kovacic-1.pdf (2012)
- "Generic Web Content Extraction with Open-Source Software" (2020; trafilatura)
- "Out-of-the-Box and Into the Ditch? Multilingual Evaluation of Generic Text Extraction Tools"
    https://hal.archives-ouvertes.fr/hal-02732851/document
    very on-topic
- https://cloud.google.com/blog/products/gcp/problem-solving-with-ml-automatic-document-classification

### Reference/Citation Extraction

"Locating and parsing bibliographic references in HTML medical articles"
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2903768/

cb2bib (in debian/ubuntu)


### Metadata Extraction

OJS 3.x seems to have `citation_fulltext_html_url`. Annoyingly, has an iframe.

http://documents.clockss.org/index.php/LOCKSS:_Extracting_Bibliographic_Metadata

https://blog.dshr.org/2013/04/talk-on-lockss-metadata-extraction-at.html

"OXPath": declaritive XPath extension for scraping metadata
https://journal.code4lib.org/articles/13007


## newspaper3k experimentation

    import newspaper

    import nltk
    nltk.download('punkt')

    # first mondays (OJS) fulltext
    monday = newspaper.Article("https://firstmonday.org/ojs/index.php/fm/article/download/10274/9729?inline=1")
    # => ugh, iframe
    monday.download()
    monday.parse() # several seconds

    monday.title
    # Surveillance, stigma and sociotechnical design for HIV
    monday.text
    # reasonable; similar to pdftotext?
    monday.authors
    # empty
    monday.images
    # reasonable?

    nih = newspaper.Article('https://www.nlm.nih.gov/pubs/techbull/ja02/ja02_locatorplus_merge.html')
    nih.download()
    nih.parse()
    nih.nlp()

    nih.title
    # Migration of Monographic Citations to LocatorPlus: Merge Project. NLM Technical Bulletin. Jul-Aug 2002
    # duplicate journal name in title
    nih.authors
    # none
    nih.text
    # Ok. missing first character, weirdly

    genders = newspaper.Article('https://web.archive.org/web/20141230080932id_/http://www.genders.org/g58/g58_fairlie.html')
    genders.download()
    genders.parse()

    genders.title
    # Presenting innovative theories in art, literature, history, music, TV and film.
    # nope: this is title of the journal

    genders.text
    # Ok. includes title and author in the body.

    dlib = newspaper.Article('http://www.dlib.org/dlib/may17/vanhyning/05vanhyning.html')
    dlib.download()
    dlib.parse()

    dlib.title
    # Transforming Libraries and Archives through Crowdsourcing
    dlib.authors()
    # none
    dlib.text
    # some other junk, but main body there

## trafilatura experimentation

    trafilatura --json -u 'http://www.dlib.org/dlib/may17/vanhyning/05vanhyning.html' | jq .

    trafilatura --xmltei -u 'http://www.dlib.org/dlib/may17/vanhyning/05vanhyning.html'

Does not work with `first_monday_ojs_inline`?

May need to test/compare more.

Examples/bugs:

    http://web.archive.org/web/20081120141035id_/http://www.mundanebehavior.org/issues/v5n1/jones.htm
    poor title detection

    generally, author detection not great.
    not, apparently, using detection of dc.authors etc
