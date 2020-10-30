
import pytest
import struct
import responses
import poppler

from sandcrawler import PdfExtractWorker, PdfExtractBlobWorker, CdxLinePusher, BlackholeSink, WaybackClient
from sandcrawler.pdfextract import process_pdf
from test_wayback import wayback_client, cdx_client


FAKE_PDF_BYTES = b"%PDF SOME JUNK" + struct.pack("!q", 112853843)

def test_process_fake_pdf():
    resp = process_pdf(FAKE_PDF_BYTES)
    print(resp)
    assert resp.status == "not-pdf"

    with open('tests/files/dummy_zip.zip', 'rb') as f:
        pdf_bytes = f.read()
    resp = process_pdf(pdf_bytes)
    assert resp.status == 'not-pdf'

@pytest.mark.skipif(poppler.version_string() == '0.71.0', reason="unsupported version of poppler")
def test_process_dummy_pdf():
    with open('tests/files/dummy.pdf', 'rb') as f:
        pdf_bytes = f.read()
    resp = process_pdf(pdf_bytes)
    assert resp.status == 'success'
    assert resp.page0_thumbnail is not None
    assert len(resp.text) > 10
    assert resp.meta_xml is None
    assert resp.file_meta['mimetype'] == 'application/pdf'
    print(resp.pdf_info)
    print(resp.pdf_extra)
    assert resp.pdf_info['Author'] == "Evangelos Vlachogiannis"
    # 595 x 842
    assert resp.pdf_extra['page0_height'] == 842
    assert resp.pdf_extra['page0_width'] == 595
    assert resp.pdf_extra['page_count'] == 1

def test_pdfextract_worker_cdx(wayback_client):

    sink = BlackholeSink()
    worker = PdfExtractWorker(wayback_client, sink=sink, thumbnail_sink=sink)

    with open('tests/files/example.cdx', 'r') as cdx_file:
        pusher = CdxLinePusher(
            worker,
            cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=['application/pdf'],
        )
        pusher_counts = pusher.run()
        assert pusher_counts['total']
        assert pusher_counts['pushed'] == 7
        assert pusher_counts['pushed'] == worker.counts['total']

def test_pdfextract_blob_worker():

    sink = BlackholeSink()
    worker = PdfExtractBlobWorker(sink=sink, thumbnail_sink=sink)

    with open('tests/files/dummy.pdf', 'rb') as f:
        pdf_bytes = f.read()

    worker.process(pdf_bytes)

