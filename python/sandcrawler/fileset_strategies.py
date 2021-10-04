
import sys
import json
import gzip
import time
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List

from sandcrawler.html_metadata import BiblioMetadata
from sandcrawler.ia import ResourceResult
from sandcrawler.fileset_types import IngestStrategy, FilesetManifestFile, DatasetPlatformItem


class FilesetIngestStrategy(class):

    def __init__():
        self.ingest_strategy = 'unknown'

    def check_existing(): # XXX: -> Any:
        raise NotImplementedError()

    def process(item: DatasetPlatformItem):
