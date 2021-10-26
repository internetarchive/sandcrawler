import pytest

from sandcrawler.workers import BlackholeSink, CdxLinePusher


def test_cdx_line_pusher():

    sink = BlackholeSink()

    # vanilla (only default filters)
    with open('tests/files/example.cdx', 'r') as cdx_file:
        pusher = CdxLinePusher(sink, cdx_file)
        counts = pusher.run()
    assert counts['total'] == 20
    assert counts['skip-parse'] == 1
    assert counts['pushed'] == 19

    # HTTP 200 and application/pdf
    with open('tests/files/example.cdx', 'r') as cdx_file:
        pusher = CdxLinePusher(sink,
                               cdx_file,
                               filter_mimetypes=['application/pdf'],
                               filter_http_statuses=[200, 226])
        counts = pusher.run()
    assert counts['total'] == 20
    assert counts['skip-parse'] == 1
    assert counts['skip-http_status'] == 10
    assert counts['skip-mimetype'] == 2
    assert counts['pushed'] == 7
