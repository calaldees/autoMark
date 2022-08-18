from functools import cached_property
from types import MappingProxyType
from zipfile import ZipFile
import io
import re
from os import environ

import requests
import xmljson

def junit_to_json(element):
    if hasattr(element, 'getroot'):
        element = element.getroot()
    if hasattr(element, '_elem'):
        element = element._elem
    data = xmljson.BadgerFish().data(element)
    return data['testsuites']['testsuite']


GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {environ['GITHUB_TOKEN']}",
}

class GithubArtifacts():
    def __init__(self, url):
        self.url = url
        self.repo = re.match(r'.*api.github.*/repos/(?P<repo>.*)/actions/runs.*/artifacts', url).group(1)  # I hate this acquisition via regex
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
    def html_url_run(self):
        workflow_id = next(a['workflow_run']['id'] for a in self.data["artifacts"])
        return f'https://github.com/{self.repo}/actions/runs/{workflow_id}'  # I hate constructing this url manually


class GithubArtifactsJUnit(GithubArtifacts):
    @property
    def junit_minidom(self):
        from xml.dom.minidom import parse as parse_xml
        return parse_xml(self.zipfile.open("junit.xml"))
    @property
    def junit_ElementTree(self):
        from xml.etree import ElementTree
        return ElementTree.parse(self.zipfile.open("junit.xml"))
        # TODO:
        # Maybe add/augment to the suite ElementTree 'properties','property', url:html_url_run
    @property
    def JUnitXml(self):
        from junitparser import JUnitXml
        return JUnitXml.fromroot(self.junit_ElementTree.getroot())
    @property
    def junit_json(self):
        return junit_to_json(self.junit_ElementTree)

    #@property
    #def report_json(self):
    #    # https://pypi.org/project/pytest-json-report/
    #    import json
    #    return json.load(self.zipfile.open("report.json"))




if __name__ == "__main__":
    aa = GithubArtifactsJUnit('https://api.github.com/repos/calaldees/frameworks_and_languages_module/actions/runs/2733608648/artifacts')

    #['testcase']

    from pprint import pprint as pp
