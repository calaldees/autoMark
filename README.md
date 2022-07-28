# autoMark
Experiment to auto mark assignments with standard open tools


TODO:
Commit in last 7 days?
Use GitHub API to get results from CI - artifacts? - junit? stats
https://docs.github.com/en/rest/reference/actions#artifacts

* github.blog [Supercharging GitHub Actions with Job Summaries](https://github.blog/2022-05-09-supercharging-github-actions-with-job-summaries/)


```python
from os import environ
from github import Github
g = Github(environ['GITHUB_TOKEN'])
r = g.get_repo('calaldees/frameworks_and_languages_module')
for f in r.get_forks():
  print(f)
print(r.get_contents("README.md").decoded_content.decode('utf8'))

r.source  # where it's forked from


def get_workflow_by_name(r, name):
    for w in r.get_workflows():
        if w.name == name:
            return w
get_workflow_by_name = lambda repo, name: next(for w in repo.get_workflows() if w.name == name, None)

w = get_workflow_by_name(r, "test_example_server")
runs = tuple(w.get_runs())
rr = runs[0]
rr.head_sha
rr.artifacts_url


```
