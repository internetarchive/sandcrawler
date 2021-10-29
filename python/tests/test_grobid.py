import json
import struct

import pytest
import responses
from test_wayback import cdx_client, wayback_client  # noqa:F401

from sandcrawler import BlackholeSink, CdxLinePusher, GrobidClient, GrobidWorker

FAKE_PDF_BYTES = b"%PDF SOME JUNK" + struct.pack("!q", 112853843)

with open("tests/files/23b29ea36382680716be08fc71aa81bd226e8a85.xml", "rb") as f:
    REAL_TEI_XML = f.read()


@pytest.fixture
def grobid_client():
    client = GrobidClient(
        host_url="http://dummy-grobid",
    )
    return client


@responses.activate
def test_grobid_503(grobid_client):

    status = b'{"status": "done broke due to 503"}'
    responses.add(
        responses.POST,
        "http://dummy-grobid/api/processFulltextDocument",
        status=503,
        body=status,
    )

    resp = grobid_client.process_fulltext(FAKE_PDF_BYTES)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert resp["status_code"] == 503
    assert resp["status"] == "error"


@responses.activate
def test_grobid_success_iso_8859(grobid_client):
    """
    This might have been the old GROBID behavior, with default encoding? Can't really remember.
    """

    responses.add(
        responses.POST,
        "http://dummy-grobid/api/processFulltextDocument",
        status=200,
        body=REAL_TEI_XML,
        content_type="text/xml",
    )

    resp = grobid_client.process_fulltext(FAKE_PDF_BYTES)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert resp["status_code"] == 200
    assert resp["status"] == "success"
    # print(type(resp['tei_xml']))
    # print(type(REAL_TEI_XML))
    assert resp["tei_xml"] == REAL_TEI_XML.decode("ISO-8859-1")


@responses.activate
def test_grobid_success(grobid_client):

    responses.add(
        responses.POST,
        "http://dummy-grobid/api/processFulltextDocument",
        status=200,
        body=REAL_TEI_XML,
        content_type="application/xml; charset=UTF-8",
    )

    resp = grobid_client.process_fulltext(FAKE_PDF_BYTES)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert resp["status_code"] == 200
    assert resp["status"] == "success"
    assert resp["tei_xml"] == REAL_TEI_XML.decode("UTF-8")


@responses.activate
def test_grobid_worker_cdx(grobid_client, wayback_client):  # noqa: F811

    sink = BlackholeSink()
    worker = GrobidWorker(grobid_client, wayback_client, sink=sink)

    responses.add(
        responses.POST,
        "http://dummy-grobid/api/processFulltextDocument",
        status=200,
        body=REAL_TEI_XML,
        content_type="text/xml",
    )

    with open("tests/files/example.cdx", "r") as cdx_file:
        pusher = CdxLinePusher(
            worker,
            cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=["application/pdf"],
        )
        pusher_counts = pusher.run()
        assert pusher_counts["total"]
        assert pusher_counts["pushed"] == 7
        assert pusher_counts["pushed"] == worker.counts["total"]

    assert len(responses.calls) == worker.counts["total"]


@responses.activate
def test_grobid_refs_978(grobid_client):

    with open("tests/files/crossref_api_work_978-3-030-64953-1_4.json", "r") as f:
        crossref_work = json.loads(f.read())

    with open("tests/files/grobid_refs_978-3-030-64953-1_4.tei.xml", "rb") as f:
        xml_bytes = f.read()
        assert "\u2013".encode("utf-8") in xml_bytes
        responses.add(
            responses.POST,
            "http://dummy-grobid/api/processCitationList",
            status=200,
            body=xml_bytes,
            content_type="application/xml; charset=UTF-8",
        )

    refs_row = grobid_client.crossref_refs(crossref_work)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert refs_row["source"] == "crossref"
    assert refs_row["source_id"] == "10.1007/978-3-030-64953-1_4"
    assert refs_row["source_ts"] == "2021-05-10T22:08:45Z"
    refs = refs_row["refs_json"]
    assert len(refs) == 3
    assert set([r["id"] for r in refs]) == set(["4_CR93", "4_CR193", "4_CR210"])

    # test case of no references
    crossref_work["message"]["reference"] = []
    refs_row = grobid_client.crossref_refs(crossref_work)

    assert refs_row["source"] == "crossref"
    assert refs_row["source_id"] == "10.1007/978-3-030-64953-1_4"
    assert refs_row["source_ts"] == "2021-05-10T22:08:45Z"
    assert len(refs_row["refs_json"]) == 0

    # test that 'message' works also
    refs_row = grobid_client.crossref_refs(crossref_work["message"])
    assert refs_row["source"] == "crossref"
    assert refs_row["source_id"] == "10.1007/978-3-030-64953-1_4"
    assert refs_row["source_ts"] == "2021-05-10T22:08:45Z"
    assert len(refs_row["refs_json"]) == 0

    # grobid gets no additional POST from the above empty queries
    assert len(responses.calls) == 1


@responses.activate
def test_grobid_refs_s104(grobid_client):

    # test another file
    with open("tests/files/crossref_api_work_s1047951103000064.json", "r") as f:
        crossref_work = json.loads(f.read())

    with open("tests/files/grobid_refs_s1047951103000064.tei.xml", "rb") as f:
        responses.add(
            responses.POST,
            "http://dummy-grobid/api/processCitationList",
            status=200,
            body=f.read(),
            content_type="application/xml; charset=UTF-8",
        )

    refs_row = grobid_client.crossref_refs(crossref_work)

    # GROBID gets one more POST
    assert len(responses.calls) == 1

    assert refs_row["source"] == "crossref"
    assert refs_row["source_id"] == "10.1017/s1047951103000064"
    assert refs_row["source_ts"] == "2021-06-10T05:35:02Z"
    refs = refs_row["refs_json"]
    assert len(refs) == 24
    assert set([r["id"] for r in refs]) == set(
        [
            "S1047951103000064_ref025",
            "S1047951103000064_ref013",
            "S1047951103000064_ref012",
            "S1047951103000064_ref041",
            "S1047951103000064_ref002",
            "S1047951103000064_ref043",
            "S1047951103000064_ref037",
            "S1047951103000064_ref035",
            "S1047951103000064_ref003",
            "S1047951103000064_ref005",
            "S1047951103000064_ref017",
            "S1047951103000064_ref016",
            "S1047951103000064_ref001",
            "S1047951103000064_ref039",
            "S1047951103000064_ref032",
            "S1047951103000064_ref014",
            "S1047951103000064_ref008",
            "S1047951103000064_ref038",
            "S1047951103000064_ref018",
            "S1047951103000064_ref027",
            "S1047951103000064_ref034",
            "S1047951103000064_ref044",
            "S1047951103000064_ref006",
            "S1047951103000064_ref030",
        ]
    )
