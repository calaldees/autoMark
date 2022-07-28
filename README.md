# autoMark
Experiment to auto mark assignments with standard open tools


TODO:
Commit in last 7 days?
Use GitHub API to get results from CI - artifacts? - junit? stats
https://docs.github.com/en/rest/reference/actions#artifacts

* github.blog [Supercharging GitHub Actions with Job Summaries](https://github.blog/2022-05-09-supercharging-github-actions-with-job-summaries/)


```python
import datetime
datetime_start = datetime.datetime.now()-datetime.timedelta(days=120)
datetime_start = datetime.datetime(year=2022, month=1, day=1)


from os import environ
from github import Github
g = Github(environ['GITHUB_TOKEN'])
r = g.get_repo('calaldees/frameworks_and_languages_module')

# ref can be omitted for HEAD
print(r.get_contents("README.md", ref="f8eca19cce30bade786a4948a2cef1c881873a3d").decoded_content.decode('utf8'))

forks = tuple(fork for fork in r.get_forks() if fork.pushed_at > datetime_start)


ff = forks[0]
ff.parent  # repository object for forked from 
ff.updated_at  # datetime of commit
ff.pushed_at  # datetime of actual push


cc = ff.get_commits(since=datetime_start, author=ff.owner)
cc[0].sha
cc[0].commit.committer.date
cc[0].files[0].filename
cc[0].files[0].patch


get_workflow_by_name = lambda repo, name: next((w for w in repo.get_workflows() if w.name == name), None)

w = get_workflow_by_name(r, "test_example_server")
runs = tuple(w.get_runs())
rr = runs[0]
rr.head_sha
rr.updated_at
rr.artifacts_url

from github_artifacts import GithubArtifactsJUnit
GithubArtifactsJUnit(rr.artifacts_url).junit_json


```
