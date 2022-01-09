"""
https://api.github.com/repos/calaldees/frameworks_and_languages_module/forks

https://github.com/calaldees/frameworks_and_languages_module/network/members

"""

import os
import subprocess
from typing import NamedTuple
import logging

import requests

log = logging.getLogger(__name__)

GITHUB_USERNAME = "calaldees"
GITHUB_REPO = "frameworks_and_languages_module"
PATH_CLONE = './clone'

from pathlib import Path
path = Path(PATH_CLONE)
path.mkdir(exist_ok=True)

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


def do():

    #from pprint import pprint
    #pprint(forks)

    log.info('get_github_forks')
    forks = tuple(map(ForkData.new, get_github_forks(GITHUB_USERNAME, GITHUB_REPO)))
    log.info(f'found {len(forks)}')

    for fork in forks:
        path_target = path.joinpath(fork.login)
        if path_target.is_dir():  # pull existing folder
            # https://stackoverflow.com/a/48566525/3356840
            log.info(f'pull: {path_target}')
            cmd_result = run_shell(['git', '-C', path_target, 'pull']) #f'git -C {path_target} pull'
            assert cmd_result.returncode == 0
        else:  # clone if not exist
            log.info(f'clone: {path_target}')
            cmd_result = run_shell(['git', 'clone', fork.clone_url, path_target])  # f'git clone {fork.clone_url} {path_target}'
            assert cmd_result.returncode == 0
            assert path_target.is_dir()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    do()
