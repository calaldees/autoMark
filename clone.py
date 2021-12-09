"""
https://api.github.com/repos/calaldees/frameworks_and_languages_module/forks

https://github.com/calaldees/frameworks_and_languages_module/network/members

"""

import os
import subprocess
from typing import NamedTuple

import requests

GITHUB_USERNAME = "calaldees"
GITHUB_REPO = "frameworks_and_languages_module"

def run_shell(cmd, _TIMEOUT_SECONDS=10):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=_TIMEOUT_SECONDS)

def get_github_forks(username, repo):
    URL_forks = f"https://api.github.com/repos/{username}/{repo}/forks"
    return requests.get(URL_forks).json()

class ForkData(NamedTuple):
    login: str
    clone_url: str
    @staticmethod
    def new(data):
        return ForkData(data['owner']['login'], data['clone_url'])

forks = tuple(map(ForkData.new, get_github_forks(GITHUB_USERNAME, GITHUB_REPO)))

for fork in forks:
    if os.path.isdir(fork.login):
        # https://stackoverflow.com/a/48566525/3356840
        cmd_result = run_shell(f'git -C {fork.login} pull')
        assert cmd_result.returncode == 0 
    else:
        print(f'git clone {fork.clone_url} {fork.login}')
        assert os.path.isdir(fork.login)

#from pprint import pprint
#pprint(forks)