from functools import partial, cache, cached_property
import datetime
from pathlib import Path
from typing import NamedTuple
from collections import defaultdict
from types import MappingProxyType

from cache_tools import cache_disk
from github_artifacts import GithubArtifactsJUnit


import logging
log = logging.getLogger(__name__)


def addClass(obj, cls):
    # https://stackoverflow.com/a/11050571/3356840
    _cls = obj.__class__
    obj.__class__ = _cls.__class__(_cls.__name__ + cls.__name__, (_cls, cls), {})

def _add_methods(obj, *methods):
    for method in methods:
        setattr(obj, method.__name__, partial(method, obj))
    return obj


from typing import Mapping, Iterable
def harden(data):
    """
    >>> harden({"a": [1,2,3]})
    mappingproxy({'a': (1, 2, 3)})
    >>> harden({"a": [1,2, {3}] })
    mappingproxy({'a': (1, 2, (3,))})
    >>> harden({"a": [1,2, {"b": 2}] })
    mappingproxy({'a': (1, 2, mappingproxy({'b': 2}))})
    >>> harden([1, {"c": True, "d": 3.14, "e": {"no", "no"}}])
    (1, mappingproxy({'c': True, 'd': 3.14, 'e': ('no',)}))
    """
    if isinstance(data, str):
        return data
    if isinstance(data, Mapping):
        return MappingProxyType({k: harden(v) for k, v in data.items()})
    if isinstance(data, Iterable):
        return tuple((harden(i) for i in data))
    return data





class GitHubForkData():
    def __init__(self, github, settings):
        self.settings = settings
        self.repo = github.get_repo(self.settings['repo'])
        self.date_start = datetime.datetime.fromisoformat(self.settings['date_start'])
        self.date_end = datetime.datetime.fromisoformat(self.settings['date_end'])
        self.timedelta = datetime.timedelta(days=int(self.settings['timedelta_days']))

    @staticmethod
    def _get_workflow_by_name(repo, name):
        return next((w for w in repo.get_workflows() if w.name == name), None)

    @cache_disk(args_to_bytes_func=lambda self, commit: commit.sha.encode('utf8'))
    def _get_workflow_artifacts(self, commit):
        def get_junit(artifacts_url):
            try:
                return GithubArtifactsJUnit(artifacts_url).junit_json
            except:
                return None
        return tuple(filter(None, (
            get_junit(artifacts_url)
            for artifacts_url in self.workflow_run_artifacts_url_lookup[commit.sha]
        )))

    @cache
    def _commits_per_week(self, repo):
        commits = defaultdict(list)
        def _commit_week_number(commit):
            return (commit.commit.committer.date - self.date_start) // self.timedelta
        for commit in repo.get_commits(since=self.date_start, author=repo.owner):
            commits[_commit_week_number(commit)].append(_add_methods(commit,
                self._get_workflow_artifacts,
            ))
        return harden(commits)

    @cached_property
    def forks(self):
        return tuple(
            _add_methods(fork, 
                self._commits_per_week,
                self._get_workflow_by_name,
            )
            for fork in self.repo.get_forks()
            if fork.pushed_at > self.date_start
        )

    @cached_property
    @cache_disk(args_to_bytes_func=lambda self: self.repo.full_name.encode('utf8'))
    def workflow_run_artifacts_url_lookup(self):
        log.info("generating workflow_run_artifacts_url_lookup")
        # TODO: progress bar?
        runs = defaultdict(list)
        #for repo in self.forks:    # TEMP HACK for development
        for repo in (self.repo, ):  # TEMP HACK for development
            for workflow in repo.get_workflows():
                if workflow.name in self.settings['workflows']:
                    for run in workflow.get_runs():
                        runs[run.head_sha].append(run.artifacts_url)
        return runs  # TODO: harden?




    @cached_property
    def data(self):
        return {
            "forks": self.forks
        }



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from pprint import pprint as pp
    import json

    datafile = Path('frameworks_and_languages.json')
    with datafile.open('rt') as filehandle:
        settings = json.load(filehandle)

    import github
    from os import environ
    g = github.Github(environ['GITHUB_TOKEN'])

    gg = GitHubForkData(g, settings)
    runs = gg.workflow_run_artifacts_url_lookup
    cc = gg._commits_per_week(gg.repo)
    art = cc[81][2]._get_workflow_artifacts()
    #cc = gg.forks[0]._commits_per_week()
    # cc[81][8]
    # 
    
    breakpoint()

    
    pp(
        gg.data
    )
