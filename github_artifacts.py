from functools import cached_property
from types import MappingProxyType
from zipfile import ZipFile
import io
import re
from os import environ

import requests

from xml.etree import ElementTree
from junitparser import JUnitXml


GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {environ['GITHUB_TOKEN']}",
}

class GithubArtifacts():
    def __init__(self, url):
        assert re.match(r'.*api.github.*actions/runs.*/artifacts', url)
        self.url = url
    @cached_property
    def data(self):
        return requests.get(self.url, headers=GITHUB_API_HEADERS).json()
    @cached_property
    def artifact_urls(self):
        return MappingProxyType({a["name"]: a["archive_download_url"] for a in self.data["artifacts"]})
    def get_zipfile(self, name):
        response = requests.get(self.artifact_urls[name], stream=True, allow_redirects=True, headers=GITHUB_API_HEADERS)
        return ZipFile(io.BytesIO(response.content))
    @property
    def zipfile(self):
        assert self.data["total_count"] == 1
        return self.get_zipfile(next(iter(self.artifact_urls.keys())))
    @property
    def junitxml(self):
        return JUnitXml.fromroot(ElementTree.parse(self.zipfile.open("junit.xml")).getroot())
        #from xml.dom.minidom import parse as parse_xml
        #return parse_xml(self.zipfile.open("junit.xml"))



if __name__ == "__main__":
    aa = GithubArtifacts('https://api.github.com/repos/calaldees/frameworks_and_languages_module/actions/runs/2733608648/artifacts')

    for testsuite in aa.junitxml:
        for test in testsuite:
            print(test)
            #breakpoint()

