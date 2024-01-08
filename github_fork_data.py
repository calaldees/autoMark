import re
import json
from functools import cache, cached_property
import datetime
from pathlib import Path
from collections import defaultdict
from typing import Sequence

from _utils import harden, _add_methods, JSONObjectEncoder
from cache_tools import cache_disk, DoNotPersistCacheException
from github_artifacts import GithubArtifactsJUnit, junit_to_json, FileNotFoundInZipfileException
from markdown_grade import markdown_grade, load_markdown

import github
from tqdm import tqdm

import logging
log = logging.getLogger(__name__)




class GitHubForkData_MarkdownTemplateMixin():
    """
    In future this will be done as junit tests on the repo itself by a github action.
    Maybe create my own 'github action' to provide the junit results on the repo directly.
    For now we can generate them here.
    """
    def _get_markdown_template(self, repo, ref=github.GithubObject.NotSet):
        try:
            return repo.get_contents(self.settings["markdown_template_filename"], ref=ref).decoded_content.decode('utf8')
        except github.GithubException:
            return ''
    def _get_markdown_json(self, repo):
        return load_markdown(self._get_markdown_template(repo))
    @cached_property
    def markdown_template(self):
        return self._get_markdown_template(self.repo)
    @cache_disk(
        args_to_bytes_func=lambda self, commit: commit.sha.encode('utf8')+b'markdown',
        ttl=datetime.timedelta(days=150),
    )
    def markdown_grade_json(self, commit):
        return junit_to_json(markdown_grade(
            template=self.markdown_template,
            target=self._get_markdown_template(repo=commit._get_repo_from_commit(), ref=commit.sha),
            url=self.markdown_html_url(commit),  # this adds a url 'property' to the testsuite
        ))
    def markdown_html_url(self, commit):
        return f'https://github.com/{commit._get_repo_from_commit().full_name}/tree/{commit.sha}/{self.settings["markdown_template_filename"]}'  # Fragile and perilous!

    @cached_property
    def fork_markdown_templates(self):
        log.info('generating markdown templates for forks')
        markdown_templates = {
            fork.owner.login: fork._get_markdown_json()
            for fork in tqdm(self.forks)
        }
        markdown_templates[''] = self._get_markdown_json(self.repo)
        return markdown_templates


class GitHubForkData(GitHubForkData_MarkdownTemplateMixin):
    def __init__(self, github, settings):
        self.github = github
        self.settings = settings
        self.date_start = datetime.datetime.fromisoformat(self.settings['date_start'])
        self.date_end = datetime.datetime.fromisoformat(self.settings['date_end'])
        self.timedelta = datetime.timedelta(days=int(self.settings['timedelta_days']))

    @staticmethod
    def _get_workflow_by_name(repo, name):
        return next((w for w in repo.get_workflows() if w.name == name), None)

    @property
    def repo(self):
        return self.get_repo(self.settings['repo'])
    @cache
    def get_repo(self, name):
        return self.github.get_repo(name)
    def _get_repo_from_commit(self, commit):
        return  self.get_repo(re.match(r'https://api.github.com/repos/(.*)/commits/.+', commit.url).group(1))  # hack to backlink to repos


    @cache
    def _commits_grouped_by_week(self, repo):
        commits = defaultdict(list)
        def _commit_week_number(commit):
            return (commit.commit.committer.date - self.date_start) // self.timedelta
        for commit in repo.get_commits(since=self.date_start, author=repo.owner):
            commits[_commit_week_number(commit)].append(_add_methods(commit,
                self._get_workflow_artifacts_junit,
                self._get_repo_from_commit,
            ))
        return harden(commits)

    @cached_property
    def forks(self):
        return tuple(
            _add_methods(fork, 
                self._get_workflow_by_name,
                self._commits_grouped_by_week,
                self._tests_grouped_by_week,
                self._get_markdown_json,  # Coupling overlap with Mixin?
            )
            #for fork in (self.repo, )  # self.repo.get_forks()  # TEMP: HACK for development
            for fork in self.repo.get_forks()
            if fork.updated_at > self.date_start    # DEBUG and fork.owner.login == 'test_username_for_debug'
        )


    @cached_property
    @cache_disk(
        args_to_bytes_func=lambda self: self.repo.full_name.encode('utf8'),
        ttl=datetime.timedelta(days=1),
    )
    def workflow_run_artifacts_url_lookup(self):
        log.info("generating workflow_run_artifacts_url_lookup")
        runs = defaultdict(list)
        for repo in tqdm(self.forks):
            for workflow in repo.get_workflows():
                if workflow.name in self.settings['workflows']:
                    for run in workflow.get_runs():
                        runs[run.head_sha].append(run.artifacts_url)
        return dict(runs)  # TODO: harden lists to tuples?

    @cache_disk(
        args_to_bytes_func=lambda self, commit: commit.sha.encode('utf8')+b'artifact',
        ttl=datetime.timedelta(days=150),
    )
    def _get_workflow_artifacts_junit(self, commit):
        artifact_urls = self.workflow_run_artifacts_url_lookup.get(commit.sha)
        if not artifact_urls:
            raise DoNotPersistCacheException()
        def get_junit(artifacts_url):
            try:
                github_artifact = GithubArtifactsJUnit(artifacts_url)
                junit_json = github_artifact.junit_json
                # HACK 
                # Normalise junit output to single dict (sometimes we get lists of suites ... investigate why this is inconsistent)
                # We want the item that actually has some tests (sometimes the RootElement has no tests ... )
                if isinstance(junit_json, Sequence):
                    for _junit_json in junit_json:
                        if _junit_json.get('@tests') > 0:
                            junit_json = _junit_json
                            break
                # HACK
                # Overlay url property - post xml - because the XML was generated on CI without knowledge of it's context/where it was run. TODO: Add this to GithubArtifactsJUnit and remove this json nonsense/hack
                junit_json.setdefault('properties',{}).setdefault('property',[]).append({"@name": "url", "@value": github_artifact.html_url_run})
                return junit_json
            except FileNotFoundInZipfileException as ex:
                log.warning(f'Run contains no JUnitXML file - {github_artifact.html_url_run=}')
            except:
                log.exception(f'Unable to get junit_json!? {artifacts_url=}')
                #breakpoint()
        return tuple(filter(None, (
            get_junit(artifacts_url) for artifacts_url in artifact_urls
        )))


    def _tests_grouped_by_week(self, repo):
        return harden({
            week_num: self._tests_from_commits(commits)
            for week_num, commits in self._commits_grouped_by_week(repo).items()
        })
    def _tests_from_commits(self, commits):
        _return = {}
        if commits:  # HACK: Generate the JUnitXml for markdown manually here in python
            # HACK - this is mad coupling with the MarkdownMixin, in future markdown marking will be done as a github action and export junit.xml file
            junit_json = self.markdown_grade_json(commits[0])  # commits are in 'latest first' order
            _return.setdefault(junit_json['@name'], junit_json)
        for commit in commits:
            for junit_json in self._get_workflow_artifacts_junit(commit) or ():
                _return.setdefault(junit_json['@name'], junit_json)
        return _return


    @cached_property
    def fork_test_data(self):
        log.info("iterating over forks")
        return {
            fork.owner.login: fork._tests_grouped_by_week()
            for fork in tqdm(self.forks)
        }



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from os import environ
    g = github.Github(environ['GITHUB_TOKEN'])

    from pprint import pprint as pp

    datafile = Path('frameworks_and_languages.json')
    with datafile.open('rt') as filehandle:
        settings = json.load(filehandle)


    gg = GitHubForkData(g, settings)
    #runs = gg.workflow_run_artifacts_url_lookup
    #cc = gg._commits_grouped_by_week(gg.repo)
    #ccc = cc[30][0]
    #art = cc[81][2]._get_workflow_artifacts_junit()
    #cc = gg.forks[0]._commits_grouped_by_week()
    #ccc = cc[81][8]
    #tt = gg._tests_grouped_by_week(gg.repo)
    #pp(gg.data)

    #breakpoint()

    with open('data.json', 'w') as filehandle:
        json.dump(gg.fork_test_data, filehandle, cls=JSONObjectEncoder)

    with open('markdown_templates.json', 'w') as filehandle:
        json.dump(gg.fork_markdown_templates, filehandle, cls=JSONObjectEncoder)
