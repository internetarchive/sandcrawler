
import requests

class GrobidClient(object):

    def __init__(self, host_uri, **kwargs):
        self.host_uri = host_uri
        self.consolidate_mode = int(kwargs.get('consolidate_mode', 1))

    def process_fulltext(self, blob, consolidate_mode=None):
        """
        Returns dict with keys:
            - status_code
            - status (slug)
            - error_msg (if status == 'error')
            - tei_xml (if status is 200)

        TODO: persist connection for performance?
        """
        assert blob

        if consolidate_mode == None:
            consolidate_mode = self.consolidate_mode

        grobid_response = requests.post(
            self.host_uri + "/api/processFulltextDocument",
            files={
                'input': blob,
                'consolidate_mode': self.consolidate_mode,
            }
        )

        info = dict(
            status_code=grobid_response.status_code,
        )
        if grobid_response.status_code == 200:
            info['status'] = 'success'
            info['tei_xml'] = grobid_response.text
        else:
            # response.text is .content decoded as utf-8
            info['status'] = 'error'
            info['error_msg'] = grobid_response.text[:10000]
        return info

