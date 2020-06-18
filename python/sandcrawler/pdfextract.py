
import sys
import datetime
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Dict, Any

import poppler
from PIL import Image

from .workers import SandcrawlerWorker, SandcrawlerFetchWorker
from .misc import gen_file_metadata
from .ia import WaybackClient, WaybackError, PetaboxError


@dataclass
class PdfExtractResult:
    sha1hex: str
    status: str
    error_msg: Optional[str] = None
    file_meta: Optional[Dict[str,Any]] = None
    text: Optional[str] = None
    page0_thumbnail: Optional[bytes] = None
    meta_xml: Optional[str] = None
    pdf_info: Optional[Dict[str,Any]] = None
    pdf_extra: Optional[Dict[str,Any]] = None
    source: Optional[Dict[str,Any]] = None

    def to_pdftext_dict(self) -> dict:
        """
        Outputs a JSON string as would be published to Kafka text/info topic.
        """
        return {
            'sha1hex': self.sha1hex,
            'status': self.status,
            'file_meta': self.file_meta,
            'error_msg': self.error_msg,
            'text': self.text,
            'page0_thumbnail': self.page0_thumbnail is not None,
            'meta_xml': self.meta_xml,
            'pdf_info': self.pdf_info,
            'pdf_extra': self.pdf_extra,
            'source': self.source,
        }


def process_pdf(blob: bytes, thumb_size=(180,300), thumb_type="JPEG") -> PdfExtractResult:
    """
    A known issue is that output text is in "physical layout" mode, which means
    columns will be side-by-side. We would prefer a single stream of tokens!

    Tried using page.text(layout_mode=poppler.TextLayout.raw_order_layout)
    instead of the default mode (poppler.TextLayout.physical_layout), but that
    didn't seem to work at all (returned empty strings).
    """
    file_meta = gen_file_metadata(blob)
    sha1hex = file_meta['sha1hex']
    if file_meta['mimetype'] != 'application/pdf':
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='not-pdf',
            error_msg=f"mimetype is '{file_meta['mimetype']}'",
            file_meta=file_meta,
        )

    try:
        pdf = poppler.load_from_data(blob)
        page0 = pdf.create_page(0)
    except NotImplementedError as e:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='parse-error',
            error_msg=str(e),
            file_meta=file_meta,
        )

    page0_thumbnail: Optional[bytes] = None
    renderer = poppler.PageRenderer()
    try:
        full_img = renderer.render_page(page0)
        img = Image.frombuffer("RGBA", (full_img.width, full_img.height), full_img.data, 'raw', "RGBA", 0, 1)
        img.thumbnail(thumb_size, Image.BICUBIC)
        buf = BytesIO()
        img.save(buf, thumb_type)
        page0_thumbnail = buf.getvalue()
        # assuming that very small images mean something went wrong
        if page0_thumbnail is None or len(page0_thumbnail) < 50:
            page0_thumbnail = None
    except Exception as e:
        print(str(e), file=sys.stderr)
        page0_thumbnail = None

    page0rect = page0.page_rect()
    full_text = page0.text()
    for n in range(1, pdf.pages):
        pageN = pdf.create_page(n)
        full_text += pageN.text()
    pdf_info = pdf.infos()
    # TODO: is this actually needed? or does json marshalling work automatically?
    for k in pdf_info.keys():
        if isinstance(pdf_info[k], datetime.datetime):
            pdf_info[k] = datetime.datetime.isoformat(pdf_info[k])

    return PdfExtractResult(
        sha1hex=sha1hex,
        file_meta=file_meta,
        status='success',
        error_msg=None,
        text=full_text or None,
        page0_thumbnail=page0_thumbnail,
        meta_xml=pdf.metadata or None,
        pdf_info=pdf.infos(),
        pdf_extra=dict(
            height=page0rect.height,
            width=page0rect.width,
            page_count=pdf.pages,
            permanent_id=pdf.pdf_id.permanent_id,
            update_id=pdf.pdf_id.update_id,
            pdf_version=f"{pdf.pdf_version[0]}.{pdf.pdf_version[1]}",
        ),
    )

class PdfExtractWorker(SandcrawlerFetchWorker):

    def __init__(self, wayback_client=None, sink=None, **kwargs):
        super().__init__(wayback_client=wayback_client)
        self.wayback_client = wayback_client
        self.sink = sink
        self.thumbnail_sink = kwargs.get('thumbnail_sink')

    def timeout_response(self, task) -> Dict:
        default_key = task['sha1hex']
        return dict(
            status="error-timeout",
            error_msg="internal GROBID worker timeout",
            source=task,
            sha1hex=default_key,
        )

    def process(self, record, key: Optional[str] = None):
        default_key = record['sha1hex']

        fetch_result = self.fetch_blob(record)
        if fetch_result['status'] != 'success':
            return fetch_result
        blob = fetch_result['blob']

        result = process_pdf(blob)
        result.source = record
        if self.thumbnail_sink and result.page0_thumbnail is not None:
            self.thumbnail_sink.push_record(result.page0_thumbnail)
        return result.to_pdftext_dict()

class PdfExtractBlobWorker(SandcrawlerWorker):
    """
    This is sort of like PdfExtractWorker, except it receives blobs directly,
    instead of fetching blobs from some remote store.
    """

    def __init__(self, sink=None, **kwargs):
        super().__init__()
        self.sink = sink
        self.thumbnail_sink = kwargs.get('thumbnail_sink')

    def process(self, blob, key: Optional[str] = None):
        if not blob:
            return None
        assert isinstance(blob, bytes)

        result = process_pdf(blob)
        if self.thumbnail_sink and result.page0_thumbnail is not None:
            self.thumbnail_sink.push_record(result.page0_thumbnail)

        return result

