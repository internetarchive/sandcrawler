
import sys
import json
import gzip
import time
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List

from sandcrawler.html_metadata import BiblioMetadata
from sandcrawler.ia import ResourceResult


class DatasetPlatformHelper(class):

    def __init__():
        self.platform_name = 'unknown'

    def match_request(request: dict , resource: ResourceResult, html_biblio: Optional[BiblioMetadata]) -> bool:
        """
        Does this request look like it matches this platform?
        """
        raise NotImplemented

    def get_item(request: dict, resource: ResourceResult, html_biblio: Optional[BiblioMetadata]) -> DatasetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """
        raise NotImplemented


class DataverseHelper(DatasetPlatformHelper):

    def __init__():
        self.platform_name = 'dataverse'

class ArchiveOrgHelper(DatasetPlatformHelper):

    def __init__():
        self.platform_name = 'archiveorg'
