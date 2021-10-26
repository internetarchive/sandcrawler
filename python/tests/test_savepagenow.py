import json

import pytest
import responses
from test_wayback import *

from sandcrawler import CdxPartial, SavePageNowClient, SavePageNowError

TARGET = "http://dummy-target.dummy"
JOB_ID = "e70f33c7-9eca-4c88-826d-26930564d7c8"
PENDING_BODY = {
    "status": "pending",
    "job_id": JOB_ID,
    "resources": [
        "https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js",
        "https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.21/jquery-ui.min.js",
        "https://cdn.onesignal.com/sdks/OneSignalSDK.js",
    ]
}
SUCCESS_BODY = {
    "status": "success",
    "job_id": JOB_ID,
    "original_url": TARGET + "/redirect",
    "screenshot": "http://web.archive.org/screenshot/http://brewster.kahle.org/",
    "timestamp": "20180326070330",
    "duration_sec": 6.203,
    "resources": [
        TARGET, TARGET + "/redirect", "http://brewster.kahle.org/",
        "http://brewster.kahle.org/favicon.ico",
        "http://brewster.kahle.org/files/2011/07/bkheader-follow.jpg",
        "http://brewster.kahle.org/files/2016/12/amazon-unhappy.jpg",
        "http://brewster.kahle.org/files/2017/01/computer-1294045_960_720-300x300.png",
        "http://brewster.kahle.org/files/2017/11/20thcenturytimemachineimages_0000.jpg",
        "http://brewster.kahle.org/files/2018/02/IMG_6041-1-300x225.jpg",
        "http://brewster.kahle.org/files/2018/02/IMG_6061-768x1024.jpg",
        "http://brewster.kahle.org/files/2018/02/IMG_6103-300x225.jpg",
        "http://brewster.kahle.org/files/2018/02/IMG_6132-225x300.jpg",
        "http://brewster.kahle.org/files/2018/02/IMG_6138-1-300x225.jpg",
        "http://brewster.kahle.org/wp-content/themes/twentyten/images/wordpress.png",
        "http://brewster.kahle.org/wp-content/themes/twentyten/style.css",
        "http://brewster.kahle.org/wp-includes/js/wp-embed.min.js?ver=4.9.4",
        "http://brewster.kahle.org/wp-includes/js/wp-emoji-release.min.js?ver=4.9.4",
        "http://platform.twitter.com/widgets.js", "https://archive-it.org/piwik.js",
        "https://platform.twitter.com/jot.html",
        "https://platform.twitter.com/js/button.556f0ea0e4da4e66cfdc182016dbd6db.js",
        "https://platform.twitter.com/widgets/follow_button.f47a2e0b4471326b6fa0f163bda46011.en.html",
        "https://syndication.twitter.com/settings",
        "https://www.syndikat.org/en/joint_venture/embed/",
        "https://www.syndikat.org/wp-admin/images/w-logo-blue.png",
        "https://www.syndikat.org/wp-content/plugins/user-access-manager/css/uamAdmin.css?ver=1.0",
        "https://www.syndikat.org/wp-content/plugins/user-access-manager/css/uamLoginForm.css?ver=1.0",
        "https://www.syndikat.org/wp-content/plugins/user-access-manager/js/functions.js?ver=4.9.4",
        "https://www.syndikat.org/wp-content/plugins/wysija-newsletters/css/validationEngine.jquery.css?ver=2.8.1",
        "https://www.syndikat.org/wp-content/uploads/2017/11/s_miete_fr-200x116.png",
        "https://www.syndikat.org/wp-includes/js/jquery/jquery-migrate.min.js?ver=1.4.1",
        "https://www.syndikat.org/wp-includes/js/jquery/jquery.js?ver=1.12.4",
        "https://www.syndikat.org/wp-includes/js/wp-emoji-release.min.js?ver=4.9.4"
    ],
    "outlinks": {
        "https://archive.org/": "xxxxxx89b-f3ca-48d0-9ea6-1d1225e98695",
        "https://other.com": "yyyy89b-f3ca-48d0-9ea6-1d1225e98695"
    }
}
ERROR_BODY = {
    "status": "error",
    "exception": "[Errno -2] Name or service not known",
    "status_ext": "error:invalid-host-resolution",
    "job_id": JOB_ID,
    "message": "Couldn't resolve host for http://example5123.com.",
    "resources": []
}
CDX_SPN_HIT = [
    [
        "urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "redirect",
        "robotflags", "length", "offset", "filename"
    ],
    [
        "wiki,fatcat)/", "20180326070330", TARGET + "/redirect", "application/pdf", "200",
        CDX_BEST_SHA1B32, "-", "-", "8445", "108062304",
        "liveweb-20200108215212-wwwb-spn04.us.archive.org-kols1pud.warc.gz"
    ],
]


@pytest.fixture
def spn_client():
    client = SavePageNowClient(
        v2endpoint="http://dummy-spnv2/save",
        ia_access_key="dummy-access-key",
        ia_secret_key="dummy-secret-key",
    )
    client.poll_seconds = 0.0
    return client


@responses.activate
def test_savepagenow_success(spn_client):

    responses.add(responses.POST,
                  'http://dummy-spnv2/save',
                  status=200,
                  body=json.dumps({
                      "url": TARGET,
                      "job_id": JOB_ID
                  }))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=200,
                  body=json.dumps(PENDING_BODY))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=200,
                  body=json.dumps(PENDING_BODY))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=200,
                  body=json.dumps(SUCCESS_BODY))

    resp = spn_client.save_url_now_v2(TARGET)

    assert len(responses.calls) == 4

    assert resp.success == True
    assert resp.status == "success"
    assert resp.request_url == TARGET
    assert resp.terminal_url == TARGET + "/redirect"
    assert resp.terminal_dt == SUCCESS_BODY['timestamp']
    assert resp.resources == SUCCESS_BODY['resources']


@responses.activate
def test_savepagenow_remote_error(spn_client):

    responses.add(responses.POST,
                  'http://dummy-spnv2/save',
                  status=200,
                  body=json.dumps({
                      "url": TARGET,
                      "job_id": JOB_ID
                  }))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=200,
                  body=json.dumps(PENDING_BODY))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=200,
                  body=json.dumps(ERROR_BODY))

    resp = spn_client.save_url_now_v2(TARGET)

    assert len(responses.calls) == 3

    assert resp.success == False
    assert resp.status == ERROR_BODY['status_ext']
    assert resp.request_url == TARGET
    assert resp.terminal_url == None
    assert resp.terminal_dt == None
    assert resp.resources == None


@responses.activate
def test_savepagenow_500(spn_client):

    responses.add(responses.POST,
                  'http://dummy-spnv2/save',
                  status=200,
                  body=json.dumps({
                      "url": TARGET,
                      "job_id": JOB_ID
                  }))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=500,
                  body=json.dumps(ERROR_BODY))

    with pytest.raises(SavePageNowError):
        resp = spn_client.save_url_now_v2(TARGET)

    assert len(responses.calls) == 2


@responses.activate
def test_crawl_resource(spn_client, wayback_client):

    responses.add(responses.POST,
                  'http://dummy-spnv2/save',
                  status=200,
                  body=json.dumps({
                      "url": TARGET,
                      "job_id": JOB_ID
                  }))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=200,
                  body=json.dumps(PENDING_BODY))
    responses.add(responses.GET,
                  'http://dummy-spnv2/save/status/' + JOB_ID,
                  status=200,
                  body=json.dumps(SUCCESS_BODY))
    responses.add(responses.GET,
                  'http://dummy-cdx/cdx',
                  status=200,
                  body=json.dumps(CDX_SPN_HIT))
    responses.add(responses.GET,
                  'https://web.archive.org/web/{}id_/{}'.format("20180326070330",
                                                                TARGET + "/redirect"),
                  status=200,
                  headers={"X-Archive-Src": "liveweb-whatever.warc.gz"},
                  body=WARC_BODY)

    print('https://web.archive.org/web/{}id_/{}'.format("20180326070330", TARGET + "/redirect"))
    resp = spn_client.crawl_resource(TARGET, wayback_client)

    assert len(responses.calls) == 5

    assert resp.hit == True
    assert resp.status == "success"
    assert resp.body == WARC_BODY
    assert resp.cdx.sha1b32 == CDX_BEST_SHA1B32

    assert type(resp.cdx) == CdxPartial
    with pytest.raises(AttributeError):
        print(resp.cdx.warc_path)
