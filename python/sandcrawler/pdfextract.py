
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
    "018dfe9824de6d2ac068ce0f7dc9961bffa1b558",
    "057c7a9dfb611bfd52f7de6c39b2d5757c5e4e53",
    "0641822e68c5a07538b967489fd19a1d5dc371a5",
    "09cba9b00494d12759c50cb914f1fb7c9746f5d1",
    "09db7c9f2efb496c974427a61e84292ae27fc702",
    "0d1c1567ea70e7b922ba88ccb868ffc7ca18e75c",
    "10c6577a658bf6203557e2998b25ea9788f8adfe",
    "182749ad1db1d5e999d07f010bdcfc2978dadc88",
    "20589d9dd0a22c8c938ad97b7f4f12648aa119fa",
    "25ab9e6169f041be05844a9b4edd6574918af769",
    "281de904c4642a9be4f17b9774fc0a2bdc8a90e3",
    "373f84dfab4ed47047826e604e2918a9cd6a95b2",
    "436c9183724f051b22c96285aa8ff1d2ba709574",
    "445968ef735b228c08c3ff4238d99fc9f4824619",
    "447fa6b5a90742a86429a932f6608d8e141688c0",
    "4c81129904f7976a50825595a3497ea7b52579ef",
    "50b3c5a3122272aca69855ef06b85d0b43a76eb1",
    "5e6a3adde9f08c276c4efd72bfacb256f2ec35d9",
    "646c4a654270606256397684204ff0f3d17be2e7",
    "64d821d728f9a3dc944b4c03be00feea0b57e314",
    "6909f0b62d8b7835de3dec7777aad7f8ef507ee3",
    "88edcbab1cac2d70af5870422974afc253f4f0c6",
    "8e4f03c29ae1fe7227140ab4b625f375f6c00d31",
    "949dfb7d833da9576b2ccb9eb1ab5457469c53d3",
    "a9162b9aef5e5da0897275fede1a6cff8cc93dfc",
    "b2b66b9c7f817a20144456f99c0be805602e8597",
    "b2d719120306b90eb8dd3580b699a61ec70556f4",
    "b5bf8b7467fb095c90adf3b49aa1687291e4469c",
    "ccb1debcfae006a3fc984e9e91309b9706a5c375",
    "cd8a7c3b8d850ebedc1ca791ccb37b9a2689f9c3",
    "d17b1e254cce82df5c6eb4fd492cef91e7e11558",
    "d188762a7e3ab5d4ee8a897204316513e4e636ec",
    "d6b0f405bf13c23d0e90c54eea527442786d1cd3",
    "e01bb7256d77aea258313bb410dfcfc10512f420",
    "eb1b39fd7a874896688855a22efddef10272427c",
    "eb5fffaa590a52bcc3705b888c6ff9c4dc4c45b2",
    "f68f9a9202a75d2aee35252e104d796f9515001e",
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

    print(f"\tpoppler processing: {sha1hex}", file=sys.stderr)
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

