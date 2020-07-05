
import sys
import json
import datetime
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Dict, Any

import poppler
from PIL import Image

from .workers import SandcrawlerWorker, SandcrawlerFetchWorker
from .misc import gen_file_metadata
from .ia import WaybackClient, WaybackError, PetaboxError


# This is a hack to work around timeouts when processing certain PDFs with
# poppler. For some reason, the usual Kafka timeout catcher isn't working on
# these, maybe due to threading.
BAD_PDF_SHA1HEX = [
    "373f84dfab4ed47047826e604e2918a9cd6a95b2",
    "64d821d728f9a3dc944b4c03be00feea0b57e314",
    "88edcbab1cac2d70af5870422974afc253f4f0c6",
    "8e4f03c29ae1fe7227140ab4b625f375f6c00d31",
    "b2b66b9c7f817a20144456f99c0be805602e8597",
    "d6b0f405bf13c23d0e90c54eea527442786d1cd3",
]

@dataclass
class PdfExtractResult:
    sha1hex: str
    status: str
    error_msg: Optional[str] = None
    file_meta: Optional[Dict[str,Any]] = None
    text: Optional[str] = None
    page0_thumbnail: Optional[bytes] = None
    has_page0_thumbnail: bool = False
    meta_xml: Optional[str] = None
    pdf_info: Optional[Dict[str,Any]] = None
    pdf_extra: Optional[Dict[str,Any]] = None
    source: Optional[Dict[str,Any]] = None

    def to_pdftext_dict(self) -> dict:
        """
        Outputs a JSON string as would be published to Kafka text/info topic.
        """
        return {
            'key': self.sha1hex,
            'sha1hex': self.sha1hex,
            'status': self.status,
            'file_meta': self.file_meta,
            'error_msg': self.error_msg,
            'text': self.text,
            'has_page0_thumbnail': self.has_page0_thumbnail,
            'meta_xml': self.meta_xml,
            'pdf_info': self.pdf_info,
            'pdf_extra': self.pdf_extra,
            'source': self.source,
        }

    @classmethod
    def from_pdftext_dict(cls, record):
        """
        Outputs a JSON string as would be published to Kafka text/info topic.
        """
        if record['status'] != 'success':
            return PdfExtractResult(
                sha1hex=record.get('sha1hex') or record['key'],
                status=record['status'],
                error_msg=record.get('error_msg'),
            )
        else:
            return PdfExtractResult(
                sha1hex=record['sha1hex'],
                status=record['status'],
                file_meta=record.get('file_meta'),
                text=record.get('text'),
                has_page0_thumbnail=bool(record.get('has_page0_thumbnail', False)),
                meta_xml=record.get('meta_xml'),
                pdf_info=record.get('pdf_info'),
                pdf_extra=record.get('pdf_extra'),
            )

    @classmethod
    def from_pdf_meta_dict(cls, record):
        """
        Parses what would be returned from postgrest
        """
        if record['status'] != 'success':
            return PdfExtractResult(
                sha1hex=record['sha1hex'],
                status=record['status'],
                error_msg=(record.get('metadata') or {}).get('error_msg'),
            )
        else:
            pdf_extra = dict()
            for k in ('page_count', 'page0_height', 'page0_width', 'permanent_id', 'pdf_version'):
                if record.get(k):
                    pdf_extra[k] = record[k]
            return PdfExtractResult(
                sha1hex=record['sha1hex'],
                status=record['status'],
                has_page0_thumbnail=bool(record.get('has_page0_thumbnail', False)),
                pdf_info=record.get('metadata'),
                pdf_extra=pdf_extra,
            )

    def to_sql_tuple(self) -> tuple:
        # pdf_meta (sha1hex, updated, status, page0_thumbnail, page_count,
        # word_count, page0_height, page0_width, permanent_id, pdf_created,
        # pdf_version, metadata)
        word_count: Optional[int] = None
        if self.text:
            word_count = len(self.text.split())
        metadata: Optional[Dict] = None
        pdf_extra = self.pdf_extra or dict()
        pdf_created = None
        # TODO: form, encrypted
        if self.pdf_info:
            metadata = dict()
            for k in ('Title', 'Subject', 'Author', 'Creator', 'Producer', 'doi'):
                if k in self.pdf_info:
                    metadata[k.lower()] = self.pdf_info[k]
            if 'CreationDate' in self.pdf_info:
                pdf_created = self.pdf_info['CreationDate']
        metadata_json: Optional[str] = None
        if metadata:
            metadata_json = json.dumps(metadata, sort_keys=True)
        return (
            self.sha1hex,
            datetime.datetime.now(), # updated
            self.status,
            self.has_page0_thumbnail,
            pdf_extra.get('page_count'),
            word_count,
            pdf_extra.get('page0_height'),
            pdf_extra.get('page0_width'),
            pdf_extra.get('permanent_id'),
            pdf_created,
            pdf_extra.get('pdf_version'),
            metadata_json,
        )


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

    if sha1hex in BAD_PDF_SHA1HEX:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='bad-pdf',
            error_msg=f"PDF known to cause processing issues",
            file_meta=file_meta,
        )

    try:
        pdf = poppler.load_from_data(blob)
        if pdf is None:
            return PdfExtractResult(
                sha1hex=sha1hex,
                status='empty-pdf',
                file_meta=file_meta,
                has_page0_thumbnail=False,
            )
        page0 = pdf.create_page(0)
        if page0 is None:
            return PdfExtractResult(
                sha1hex=sha1hex,
                status='empty-page0',
                file_meta=file_meta,
            )
        # this call sometimes fails an returns an AttributeError
        page0rect = page0.page_rect()
    except (AttributeError, poppler.document.LockedDocumentError) as e:
        # may need to expand the set of exceptions caught here over time, but
        # starting with a narrow set
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='parse-error',
            error_msg=str(e),
            file_meta=file_meta,
        )

    assert page0 is not None
    page0_thumbnail: Optional[bytes] = None
    renderer = poppler.PageRenderer()
    try:
        full_img = renderer.render_page(page0)
        img = Image.frombuffer("RGBA", (full_img.width, full_img.height), full_img.data, 'raw', "BGRA", 0, 1)
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

    try:
        full_text = page0.text()
        for n in range(1, pdf.pages):
            pageN = pdf.create_page(n)
            full_text += pageN.text()
    except AttributeError as e:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='parse-error',
            error_msg=str(e),
            file_meta=file_meta,
        )

    # Kafka message size limit; cap at about 1 MByte
    if len(full_text)> 1000000:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='text-too-large',
            error_msg="full_text chars: {}".format(len(full_text)),
            file_meta=file_meta,
        )
    if len(pdf.metadata)> 1000000:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='text-too-large',
            error_msg="meta_xml chars: {}".format(len(full_text)),
            file_meta=file_meta,
        )

    try:
        pdf_info = pdf.infos()
    except UnicodeDecodeError:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status='bad-unicode',
            error_msg="in infos()",
            file_meta=file_meta,
        )

    # TODO: is this actually needed? or does json marshalling work automatically?
    for k in pdf_info.keys():
        if isinstance(pdf_info[k], datetime.datetime):
            pdf_info[k] = datetime.datetime.isoformat(pdf_info[k])

    permanent_id: Optional[str] = None
    update_id: Optional[str] = None
    try:
        permanent_id = pdf.pdf_id.permanent_id
        update_id = pdf.pdf_id.update_id
    except TypeError:
        pass

    return PdfExtractResult(
        sha1hex=sha1hex,
        file_meta=file_meta,
        status='success',
        error_msg=None,
        text=full_text or None,
        has_page0_thumbnail=page0_thumbnail is not None,
        page0_thumbnail=page0_thumbnail,
        meta_xml=pdf.metadata or None,
        pdf_info=pdf_info,
        pdf_extra=dict(
            page0_height=page0rect.height,
            page0_width=page0rect.width,
            page_count=pdf.pages,
            permanent_id=permanent_id,
            update_id=update_id,
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
            error_msg="internal pdf-extract worker timeout",
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
            self.thumbnail_sink.push_record(result.page0_thumbnail, key=result.sha1hex)
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
            self.thumbnail_sink.push_record(result.page0_thumbnail, key=result.sha1hex)

        return result.to_pdftext_dict()

