import datetime
import json
import sys
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import poppler
from PIL import Image

from .ia import WaybackClient
from .misc import gen_file_metadata
from .workers import SandcrawlerFetchWorker, SandcrawlerWorker

# This is a hack to work around timeouts when processing certain PDFs with
# poppler. For some reason, the usual Kafka timeout catcher isn't working on
# these, maybe due to threading.
BAD_PDF_SHA1HEX: List[str] = [
    "011478a1e63a2a31eae1a93832a74cc95f220760",
    "018dfe9824de6d2ac068ce0f7dc9961bffa1b558",
    "057c7a9dfb611bfd52f7de6c39b2d5757c5e4e53",
    "06061af0707298c12932516d1bb7c2b6dc443824",
    "0641822e68c5a07538b967489fd19a1d5dc371a5",
    "09cba9b00494d12759c50cb914f1fb7c9746f5d1",
    "09db7c9f2efb496c974427a61e84292ae27fc702",
    "0a1c13cb8783bbbf248b2345b9890e2410aa3f0a",
    "0ccc6dc94f4e2d809fac8543870265c3421f3c9e",
    "0d1c1567ea70e7b922ba88ccb868ffc7ca18e75c",
    "10c6577a658bf6203557e2998b25ea9788f8adfe",
    "15a720921ce30da983fcd1bfa7fe9aeeda503e41",
    "1659881a31edc2d0e170f6bb26d32e74cc4ca387",
    "17e679b0ec9444fff2ea4d02caec05dd2de80ec3",
    "182749ad1db1d5e999d07f010bdcfc2978dadc88",
    "1a17a4fc43397804830cc29021281aac2e8cf0cb",
    "1cb166f0c0b5ffe673e6bbf6a29d77278711f253",
    "1d04e46b6848e6479dd90fe26bb11627044fb664",
    "1d967c95546d31edaaf0c3ef9ffcc11113a9e11a",
    "1f90194bf0c7fff1fe1ed5fff77a934c7a1b32a0",
    "20589d9dd0a22c8c938ad97b7f4f12648aa119fa",
    "2195e528fa1cf5f8ae3b2adcc516896016c3411f",
    "25ab9e6169f041be05844a9b4edd6574918af769",
    "281de904c4642a9be4f17b9774fc0a2bdc8a90e3",
    "2bd5322975653536550a039eb055174b2bf241b3",
    "2fc64da736175810918fd32c94c5068b0d660bcc",
    "32318fba9b05b2756b7362bcaa4722c92ed8d449",
    "336833c6fc968cd0938250dfc93c032a30111cfc",
    "362ad00bc24d650c8f11851f9e554fc560b73e7a",
    "373f84dfab4ed47047826e604e2918a9cd6a95b2",
    "3ac0b6e17e30d141871a0a5b127536919fe5aa19",
    "3c8a6a708da0dc1802f5f3e5267a49b3c25e1ffe",
    "3e5f9fb94e7314447a22f3d009419a922136177f",
    "3fad493c940137ce703f2f570ebb504e360c6df3",
    "40aa94602ab13e5a7d9df8c989fca4fa5c01239e",
    "427479c94d7d0e512f898bc7ff0b6f210069f902",
    "436c9183724f051b22c96285aa8ff1d2ba709574",
    "43a8c0abf0386d3e3397cf5e22a884761dd63db7",
    "445968ef735b228c08c3ff4238d99fc9f4824619",
    "447fa6b5a90742a86429a932f6608d8e141688c0",
    "45f014d7d631559dc7726e5c5513f1e7c91c48a9",
    "47577ff6d6876117ca69bec60a5764f7d2c2ec70",
    "4785181cec8944eee00ddb631a5dfc771b89bab7",
    "47db2db2cc976429568841a0496c0ab4ed7b5977",
    "481c0bae81873988fcc8662ba8a269e8823fdea2",
    "4c81129904f7976a50825595a3497ea7b52579ef",
    "4edc1402712fa6827c4501fed8042e9f4447829c",
    "50b3c5a3122272aca69855ef06b85d0b43a76eb1",
    "52fc9b3c5199ef395d410c7cee5961dc812e4d29",
    "53471346019947a88c1ba141fb829375527153b0",
    "58d9ae7dcb0a7dbbdfc58ad266030b037e9cd0ff",
    "59cfc843ebdb1c1e5db1efc76a40f46cb3bb06f0",
    "5ab98405b676ee81a6ca74fba51a9e4a6cff7311",
    "5e04779cbbae5ce88bb786064f756885dd6895fe",
    "5e6a3adde9f08c276c4efd72bfacb256f2ec35d9",
    "623ff84b616383d0a3e0dd8dbce12f0b5fe9a6ac",
    "646c4a654270606256397684204ff0f3d17be2e7",
    "64d821d728f9a3dc944b4c03be00feea0b57e314",
    "668b7d777203af4b261d21bf4669fc9b385062e1",
    "689b5cb3ddef213d612363a903f10d0358ea64d2",
    "6909f0b62d8b7835de3dec7777aad7f8ef507ee3",
    "74e617dc95555e8ca3aadd19d0c85b71cd77d1d9",
    "75c2662a96ccc48891228df7c85eb7d4da9dd621",
    "771f1ca0007a6fbed5b4a434c73f524f715d33c1",
    "776859635e9dc01d97b0582f49c814ffbcb019fb",
    "781dafda896a9f5c30f3d0a011f79a3b79b574c4",
    "788672c7c2bcdecf6e2f6a2177c01e60f04d9cfb",
    "79d6cba3c6e577a0f3a3a9fe575680d38454938d",
    "7cfc0739be9c49d94272110a0a748256bdde9be6",
    "7daf61526ec825151f384cc1db510ca5237d5d80",
    "7e9d846f3bf9ce15cdb991b78cc870ab8a2bed76",
    "8398b211a5ec4da1195a4ba1bc29ca8c0ac40f67",
    "859d7ec532a0bf3b52b17c7f2d8ecc58410c0aad",
    "88edcbab1cac2d70af5870422974afc253f4f0c6",
    "89860fc475fcb2a2d86c4544df52ec8fd5e6533f",
    "8dcaf4ef132900dd378f7be526c884b17452713b",
    "8e4f03c29ae1fe7227140ab4b625f375f6c00d31",
    "949dfb7d833da9576b2ccb9eb1ab5457469c53d3",
    "961ec451172f373f919c593737466300e42062cb",
    "976989fa6e447578d9ce16ec5b526f0e09d6df50",
    "98b02eb70066c182c705ef4d14d8b723ad7f1fab",
    "993ca31f6974f8387bb18dd7d38987d290da8781",
    "9dbd05af3442e6f42d67868054751b76973f4171",
    "a2298c137b9c8c8975bad62eea9224edb95e6952",
    "a2671738755ab8b24775e95375dc72f1ca4e5fd6",
    "a26f299fb97c646effeebd4c5e2968786bd0f781",
    "a48f9b7ad627909f76d780aa4208530304ece42c",
    "a69665d0b5d3b95f54f68406eee3ed50c67efb45",
    "a69665d0b5d3b95f54f68406eee3ed50c67efb45",
    "a8357c31837404f9ebd798999d546c9398ab3648",
    "a9162b9aef5e5da0897275fede1a6cff8cc93dfc",
    "abc9d264df446707b40d7c9f79befd0f89291e59",
    "ad038725bf6855a79f3c768ebe93c7103d14522f",
    "aef581bf42e76e527f5aed3b8958fd4e7a24819f",
    "b2b66b9c7f817a20144456f99c0be805602e8597",
    "b2d719120306b90eb8dd3580b699a61ec70556f4",
    "b4b8e18e27f102e59b2be2d58c7b54d0a0eb457a",
    "b5be7f409a3a2601208c5ce08cf52b9ac1094aae",
    "b5bf8b7467fb095c90adf3b49aa1687291e4469c",
    "b8b427e5b3d650ba9e03197f9c3917e25b878930",
    "bad48b89b639b5b7df2c6a2d5288181fcb8b0e35",
    "be0cda7642e9247b3ee41cd2017fa709aab4f344",
    "c1b583fbd052572f08158d39ffe4d7510dadbebb",
    "c2526f75a013dc67b14ce1e2d0e4fc80bb93c6e1",
    "c4abbb284f4acaca9e8ceb88f842901984e84d33",
    "c7220d1bf1e71fb755d9f26bbdd4c539dc162960",
    "c7687fa6f637c7d32a25be0e772867d87536d35c",
    "c7d8b37ec99cf0d987e60667f05299f200e18a5d",
    "c92b9ae9eefa07504950b405625aef54b48f0e1a",
    "ccb1debcfae006a3fc984e9e91309b9706a5c375",
    "cd611c765cbb0b3b7cb2fdc07d8f0b9cc93ec257",
    "cd8a7c3b8d850ebedc1ca791ccb37b9a2689f9c3",
    "d055c054c330f99ec011e37186d2b429339758fd",
    "d17b1e254cce82df5c6eb4fd492cef91e7e11558",
    "d188762a7e3ab5d4ee8a897204316513e4e636ec",
    "d613b9e4442f5d5d19ea6814fa9729bff7da7c85",
    "d6b0f405bf13c23d0e90c54eea527442786d1cd3",
    "da2211ee2dbc6dda36571976d810e2366a3d2504",
    "e01bb7256d77aea258313bb410dfcfc10512f420",
    "e2bf5d0a5885359381fe8ef2cd9290171d494e9b",
    "e2c3b8a2cf33d5e8972bc9ddb78373766a75e412",
    "e64714a81f60ab9286ec90cad682cb22e564fb6f",
    "e9d7716b4f94bbc3d94459b5fe9bb8b15cb2e433",
    "e9e84e17383e93a784a8471708619162b32fb399",
    "eac7df5f799983d5a7cc55d10b4d426dc557febf",
    "eaf84b2efd2f69c7b3f407f89ea66ac4c41fac36",
    "eb1b39fd7a874896688855a22efddef10272427c",
    "eb5fffaa590a52bcc3705b888c6ff9c4dc4c45b2",
    "edf8dcc8736f06afbaca0e01d60bd2c475403a3d",
    "ee2ee6ae2cf05128810d0d95bbe69bd263e140de",
    "ee9530a2c5a3d1e3813ccb51a55cc8b0d9b5dfc7",
    "ef1dfa325c21cff4cd8bb1a9b6c4ee6996d43c8f",
    "ef6749d9263a01f921ba7d72df0d17671d14e5f6",
    "f0ea221d8587cede25592266486e119d277f7096",
    "f68f9a9202a75d2aee35252e104d796f9515001e",
    "f9314d3bf2eac78a7d78d18adcccdb35542054ef",
    "fd9bd560662e070b222d63052830837829c490f0",
]


@dataclass
class PdfExtractResult:
    sha1hex: str
    status: str
    error_msg: Optional[str] = None
    file_meta: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    page0_thumbnail: Optional[bytes] = None
    has_page0_thumbnail: bool = False
    meta_xml: Optional[str] = None
    pdf_info: Optional[Dict[str, Any]] = None
    pdf_extra: Optional[Dict[str, Any]] = None
    source: Optional[Dict[str, Any]] = None

    def to_pdftext_dict(self) -> dict:
        """
        Outputs a JSON string as would be published to Kafka text/info topic.
        """
        return {
            "key": self.sha1hex,
            "sha1hex": self.sha1hex,
            "status": self.status,
            "file_meta": self.file_meta,
            "error_msg": self.error_msg,
            "text": self.text,
            "has_page0_thumbnail": self.has_page0_thumbnail,
            "meta_xml": self.meta_xml,
            "pdf_info": self.pdf_info,
            "pdf_extra": self.pdf_extra,
            "source": self.source,
        }

    @staticmethod
    def from_pdftext_dict(record: Dict[str, Any]) -> "PdfExtractResult":
        """
        Outputs a JSON string as would be published to Kafka text/info topic.
        """
        if record["status"] != "success":
            return PdfExtractResult(
                sha1hex=record.get("sha1hex") or record["key"],
                status=record["status"],
                error_msg=record.get("error_msg"),
            )
        else:
            return PdfExtractResult(
                sha1hex=record["sha1hex"],
                status=record["status"],
                file_meta=record.get("file_meta"),
                text=record.get("text"),
                has_page0_thumbnail=bool(record.get("has_page0_thumbnail", False)),
                meta_xml=record.get("meta_xml"),
                pdf_info=record.get("pdf_info"),
                pdf_extra=record.get("pdf_extra"),
            )

    @staticmethod
    def from_pdf_meta_dict(record: Dict[str, Any]) -> "PdfExtractResult":
        """
        Parses what would be returned from postgrest
        """
        if record["status"] != "success":
            return PdfExtractResult(
                sha1hex=record["sha1hex"],
                status=record["status"],
                error_msg=(record.get("metadata") or {}).get("error_msg"),
            )
        else:
            pdf_extra = dict()
            for k in (
                "page_count",
                "page0_height",
                "page0_width",
                "permanent_id",
                "pdf_version",
            ):
                if record.get(k):
                    pdf_extra[k] = record[k]
            return PdfExtractResult(
                sha1hex=record["sha1hex"],
                status=record["status"],
                has_page0_thumbnail=bool(record.get("has_page0_thumbnail", False)),
                pdf_info=record.get("metadata"),
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
            for k in ("Title", "Subject", "Author", "Creator", "Producer", "doi"):
                if k in self.pdf_info:
                    metadata[k.lower()] = self.pdf_info[k]
            if "CreationDate" in self.pdf_info:
                pdf_created = self.pdf_info["CreationDate"]
        metadata_json: Optional[str] = None
        if metadata:
            metadata_json = json.dumps(metadata, sort_keys=True)
        return (
            self.sha1hex,
            datetime.datetime.now(),  # updated
            self.status,
            self.has_page0_thumbnail,
            pdf_extra.get("page_count"),
            word_count,
            pdf_extra.get("page0_height"),
            pdf_extra.get("page0_width"),
            pdf_extra.get("permanent_id"),
            pdf_created,
            pdf_extra.get("pdf_version"),
            metadata_json,
        )


def process_pdf(
    blob: bytes, thumb_size: Tuple[int, int] = (180, 300), thumb_type: str = "JPEG"
) -> PdfExtractResult:
    """
    A known issue is that output text is in "physical layout" mode, which means
    columns will be side-by-side. We would prefer a single stream of tokens!

    Tried using page.text(layout_mode=poppler.TextLayout.raw_order_layout)
    instead of the default mode (poppler.TextLayout.physical_layout), but that
    didn't seem to work at all (returned empty strings).
    """
    file_meta = gen_file_metadata(blob)
    sha1hex = file_meta["sha1hex"]
    if file_meta["mimetype"] != "application/pdf":
        return PdfExtractResult(
            sha1hex=sha1hex,
            status="not-pdf",
            error_msg=f"mimetype is '{file_meta['mimetype']}'",
            file_meta=file_meta,
        )

    if sha1hex in BAD_PDF_SHA1HEX:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status="bad-pdf",
            error_msg="PDF known to cause processing issues",
            file_meta=file_meta,
        )

    print(f"\tpoppler processing: {sha1hex}", file=sys.stderr)
    try:
        pdf = poppler.load_from_data(blob)
        if pdf is None:
            return PdfExtractResult(
                sha1hex=sha1hex,
                status="empty-pdf",
                file_meta=file_meta,
                has_page0_thumbnail=False,
            )
        page0 = pdf.create_page(0)
        if page0 is None:
            return PdfExtractResult(
                sha1hex=sha1hex,
                status="empty-page0",
                file_meta=file_meta,
            )
        # this call sometimes fails an returns an AttributeError
        page0rect = page0.page_rect()
    except (AttributeError, poppler.document.LockedDocumentError) as e:
        # may need to expand the set of exceptions caught here over time, but
        # starting with a narrow set
        return PdfExtractResult(
            sha1hex=sha1hex,
            status="parse-error",
            error_msg=str(e),
            file_meta=file_meta,
        )

    assert page0 is not None
    page0_thumbnail: Optional[bytes] = None
    renderer = poppler.PageRenderer()
    try:
        full_img = renderer.render_page(page0)
        img = Image.frombuffer(
            "RGBA", (full_img.width, full_img.height), full_img.data, "raw", "BGRA", 0, 1
        )
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
            status="parse-error",
            error_msg=str(e),
            file_meta=file_meta,
        )

    # Kafka message size limit; cap at about 1 MByte
    if len(full_text) > 1000000:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status="text-too-large",
            error_msg="full_text chars: {}".format(len(full_text)),
            file_meta=file_meta,
        )
    if len(pdf.metadata) > 1000000:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status="text-too-large",
            error_msg="meta_xml chars: {}".format(len(full_text)),
            file_meta=file_meta,
        )

    try:
        pdf_info = pdf.infos()
    except UnicodeDecodeError:
        return PdfExtractResult(
            sha1hex=sha1hex,
            status="bad-unicode",
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
        status="success",
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
    def __init__(
        self,
        wayback_client: Optional[WaybackClient] = None,
        sink: Optional[SandcrawlerWorker] = None,
        **kwargs,
    ):
        super().__init__(wayback_client=wayback_client)
        self.wayback_client = wayback_client
        self.sink = sink
        self.thumbnail_sink = kwargs.get("thumbnail_sink")

    def timeout_response(self, task: Dict[str, Any]) -> Dict[str, Any]:
        default_key = task["sha1hex"]
        return dict(
            status="error-timeout",
            error_msg="internal pdf-extract worker timeout",
            source=task,
            sha1hex=default_key,
        )

    def process(self, record: Any, key: Optional[str] = None) -> dict:
        fetch_result = self.fetch_blob(record)
        if fetch_result["status"] != "success":
            return fetch_result
        blob: bytes = fetch_result["blob"]
        assert blob and isinstance(blob, bytes)

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

    def __init__(self, sink: Optional[SandcrawlerWorker] = None, **kwargs):
        super().__init__()
        self.sink = sink
        self.thumbnail_sink = kwargs.get("thumbnail_sink")

    def process(self, blob: Any, key: Optional[str] = None) -> Any:
        if not blob:
            return None
        assert isinstance(blob, bytes)

        result = process_pdf(blob)
        if self.thumbnail_sink and result.page0_thumbnail is not None:
            self.thumbnail_sink.push_record(result.page0_thumbnail, key=result.sha1hex)

        return result.to_pdftext_dict()
