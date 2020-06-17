
status: work-in-progress

New PDF derivatives: thumbnails, metadata, raw text
===================================================

To support scholar.archive.org (fulltext search) and other downstream uses of
fatcat, want to extract from many PDFs:

- pdf structured metadata
- thumbnail images
- raw extracted text

A single worker should extract all of these fields, and publish in to two kafka
streams. Separate persist workers consume from the streams and push in to SQL
and/or seaweedfs.

Additionally, this extraction should happen automatically for newly-crawled
PDFs as part of the ingest pipeline. When possible, checks should be run
against the existing SQL table to avoid duplication of processing.


## PDF Metadata and Text

Kafka topic (name: `sandcrawler-ENV.pdftext`; 12x partitions; gzip
compression) JSON schema:

    sha1hex (string; used as key)
    status (string)
    text (string)
    page0_thumbnail (boolean)
    meta_xml (string)
    pdf_info (object)
    pdf_extra (object)
        word_count
    file_meta (object)
    source (object)

For the SQL table we should have columns for metadata fields that are *always*
saved, and put a subset of other interesting fields in a JSON blob. We don't
need all metadata fields in SQL. Full metadata/info will always be available in
Kafka, and we don't want SQL table size to explode. Schema:

    CREATE TABLE IF NOT EXISTS pdf_meta (
        sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
        updated             TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        status              TEXT CHECK (octet_length(status) >= 1) NOT NULL,
        page0_thumbnail     BOOLEAN NOT NULL,
        page_count          INT CHECK (page_count >= 0),
        word_count          INT CHECK (word_count >= 0),
        page0_height        FLOAT CHECK (page0_height >= 0),
        page0_width         FLOAT CHECK (page0_width >= 0),
        permanent_id        TEXT CHECK (octet_length(permanent_id) >= 1),
        creation date       TIMESTAMP WITH TIME ZONE,
        pdf_version         TEXT CHECK (octet_length(pdf_version) >= 1),
        metadata            JSONB;
        -- maybe some analysis of available fields?
        -- metadata JSON fields:
        --    title
        --    subject
        --    author
        --    creator
        --    producer
        --    CrossMarkDomains
        --    doi
        --    form
        --    encrypted
    );


## Thumbnail Images

Kafka Schema is raw image bytes as message body; sha1sum of PDF as the key. No
compression, 12x partitions.

Topic name is `sandcrawler-ENV.thumbnail-SIZE-png`. Thus, topic name contains
the "metadata" of thumbail size/shape.

Have decided to use JPEG thumbnails, 180px wide (and max 300px high, though
width restriction is almost always the limiting factor). This size matches that
used on archive.org, and is slightly larger than the thumbnails currently used
on scholar.archive.org prototype. We intend to tweak the scholar.archive.org
CSS to use the full/raw thumbnail image at max desktop size. At this size it
would be difficult (though maybe not impossible?) to extract text (other than
large-font titles).


### Implementation

We use the `poppler` CPP library (wrapper for python) to extract and convert everything.

Some example usage of the `python-poppler` library:

    import poppler
    from PIL import Image

    pdf = poppler.load_from_file("/home/bnewbold/10.1038@s41551-020-0534-9.pdf")          
    pdf.pdf_id
    page = pdf.create_page(0)
    page.page_rect().width

    renderer = poppler.PageRenderer()
    full_page = renderer.render_page(page)
    img = Image.frombuffer("RGBA", (full_page.width, full_page.height), full_page.data, 'raw', "RGBA")
    img.thumbnail((180,300), Image.BICUBIC)
    img.save("something.jpg")

## Deployment and Infrastructure

Deployment will involve:

- sandcrawler DB SQL table
    => guesstimate size 100 GByte for hundreds of PDFs
- postgrest/SQL access to new table for internal HTTP API hits
- seaweedfs raw text folder
    => reuse existing bucket with GROBID XML; same access restrictions on content
- seaweedfs thumbnail bucket
    => new bucket for this world-public content
- public nginx access to seaweed thumbnail bucket
- extraction work queue kafka topic
    => same schema/semantics as ungrobided
- text/metadata kafka topic
- thumbnail kafka topic
- text/metadata persist worker(s)
    => from kafka; metadata to SQL database; text to seaweedfs blob store
- thumbnail persist worker
    => from kafka to seaweedfs blob store
- pdf extraction worker pool
    => very similar to GROBID worker pool
- ansible roles for all of the above

Plan for processing/catchup is:

- test with COVID-19 PDF corpus
- run extraction on all current fatcat files avaiable via IA
- integrate with ingest pipeline for all new files
- run a batch catchup job over all GROBID-parsed files with no pdf meta
  extracted, on basis of SQL table query

## Appendix: Thumbnail Size and Format Experimentation

Using 190 PDFs from `/data/pdfs/random_crawl/files` on my laptop to test.

TODO: actually, 4x images failed to convert with pdftocairo; this throws off
"mean" sizes by a small amount.

    time ls | parallel -j1 pdftocairo -singlefile -scale-to 200 -png {} /tmp/test-png/{}.png
    real    0m29.314s
    user    0m26.794s
    sys     0m2.484s
    => missing: 4
    => min: 0.8k
    => max: 57K
    => mean: 16.4K
    => total: 3120K

    time ls | parallel -j1 pdftocairo -singlefile -scale-to 200 -jpeg {} /tmp/test-jpeg/{}.jpg
    real    0m26.289s
    user    0m24.022s
    sys     0m2.490s
    => missing: 4
    => min: 1.2K
    => max: 13K
    => mean: 8.02k
    => total: 1524K

    time ls | parallel -j1 pdftocairo -singlefile -scale-to 200 -jpeg -jpegopt optimize=y,quality=80 {} /tmp/test-jpeg2/{}.jpg
    real    0m27.401s
    user    0m24.941s
    sys     0m2.519s
    => missing: 4
    => min: 577
    => max: 14K
    => mean:
    => total: 1540K

    time ls | parallel -j1 convert -resize 200x200 {}[0] /tmp/magick-png/{}.png
    => missing: 4
    real    1m19.399s
    user    1m17.150s
    sys     0m6.322s
    => min: 1.1K
    => max: 325K
    => mean:
    => total: 8476K

    time ls | parallel -j1 convert -resize 200x200 {}[0] /tmp/magick-jpeg/{}.jpg
    real    1m21.766s
    user    1m17.040s
    sys     0m7.155s
    => total: 3484K

NOTE: the following `pdf_thumbnail.py` images are somewhat smaller than the above
jpg and pngs (max 180px wide, not 200px wide)

    time ls | parallel -j1 ~/code/sandcrawler/python/scripts/pdf_thumbnail.py {} /tmp/python-png/{}.png
    real    0m48.198s
    user    0m42.997s
    sys     0m4.509s
    => missing: 2; 2x additional stub images
    => total: 5904K

    time ls | parallel -j1 ~/code/sandcrawler/python/scripts/pdf_thumbnail.py {} /tmp/python-jpg/{}.jpg
    real    0m45.252s
    user    0m41.232s
    sys     0m4.273s
    => min: 1.4K
    => max: 16K
    => mean: ~9.3KByte
    => total: 1772K

    time ls | parallel -j1 ~/code/sandcrawler/python/scripts/pdf_thumbnail.py {} /tmp/python-jpg-360/{}.jpg
    real    0m48.639s
    user    0m44.121s
    sys     0m4.568s
    => mean: ~28k
    => total: 5364K (3x of 180px batch)

    quality=95
    time ls | parallel -j1 ~/code/sandcrawler/python/scripts/pdf_thumbnail.py {} /tmp/python-jpg2-360/{}.jpg
    real    0m49.407s
    user    0m44.607s
    sys     0m4.869s
    => total: 9812K

    quality=95
    time ls | parallel -j1 ~/code/sandcrawler/python/scripts/pdf_thumbnail.py {} /tmp/python-jpg2-180/{}.jpg
    real    0m45.901s
    user    0m41.486s
    sys     0m4.591s
    => mean: 16.4K
    => total: 3116K

At the 180px size, the difference between default and quality=95 seems
indistinguishable visually to me, but is more than a doubling of file size.
Also tried at 300px and seems near-indistinguishable there as well.

At a mean of 10 Kbytes per file:

    10  million -> 100 GBytes
    100 million -> 1 Tbyte

Older COVID-19 thumbnails were about 400px wide:

    pdftocairo -png -singlefile -scale-to-x 400 -scale-to-y -1

Display on scholar-qa.archive.org is about 135x181px

archive.org does 180px wide

Unclear if we should try to do double resolution for high DPI screens (eg,
apple "retina").

Using same size as archive.org probably makes the most sense: max 180px wide,
preserve aspect ratio. And jpeg improvement seems worth it.

#### Merlijn notes

From work on optimizing microfilm thumbnail images:

    When possible, generate a thumbnail that fits well on the screen of the
    user.  Always creating a large thumbnail will result in the browsers
    downscaling them, leading to fuzzy text. If it’s not possible, then create
    the pick the resolution you’d want to support (1.5x or 2x scaling) and
    create thumbnails of that size, but also apply the other recommendations
    below - especially a sharpening filter.

    Use bicubic or lanczos interpolation. Bilinear and nearest neighbour are
    not OK.

    For text, consider applying a sharpening filter. Not a strong one, but some
    sharpening can definitely help.


## Appendix: PDF Info Fields

From `pdfinfo` manpage:

    The ´Info' dictionary contains the following values:

        title
        subject
        keywords
        author
        creator
        producer
        creation date
        modification date

    In addition, the following information is printed:

        tagged (yes/no)
        form (AcroForm / XFA / none)
        javascript (yes/no)
        page count
        encrypted flag (yes/no)
        print and copy permissions (if encrypted)
        page size
        file size
        linearized (yes/no)
        PDF version
        metadata (only if requested)

For an example file, the output looks like:

    Title:          A mountable toilet system for personalized health monitoring via the analysis of excreta
    Subject:        Nature Biomedical Engineering, doi:10.1038/s41551-020-0534-9
    Keywords:       
    Author:         Seung-min Park
    Creator:        Springer
    CreationDate:   Thu Mar 26 01:26:57 2020 PDT
    ModDate:        Thu Mar 26 01:28:06 2020 PDT
    Tagged:         no
    UserProperties: no
    Suspects:       no
    Form:           AcroForm
    JavaScript:     no
    Pages:          14
    Encrypted:      no
    Page size:      595.276 x 790.866 pts
    Page rot:       0
    File size:      6104749 bytes
    Optimized:      yes
    PDF version:    1.4

For context on the `pdf_id` fields ("original" and "updated"), read:
<https://web.hypothes.is/blog/synchronizing-annotations-between-local-and-remote-pdfs/>
