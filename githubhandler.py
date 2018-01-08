#!/usr/env/python

import requests
import time
import os
import base64
import json


class GithubHandler(object):

    GH_API_BASE_URL = 'https://api.github.com'
    GH_API_TOKEN = 'asdfaskfjasdklfasdfdasfas'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {'Authorization': 'token {}'.format(self.GH_API_TOKEN)})

    def perform_file_update_with_pull_request(self, repo_full_name, path, updated_content, message):

        local_owner = self._perform_gh_request('GET', '/user').json()['login']
        repo = os.path.basename(repo_full_name)

        self._perform_gh_request('DELETE', '/repos/{}/{}'.format(local_owner, repo), ok_status=[404])
        #self._perform_gh_request('GET', '/repos/{}/{}'.format(local_owner, repo), ok_status=[404], retry_until_status=404)
        self._perform_gh_request('POST', '/repos/{}/forks'.format(repo_full_name))

        obj_in_fork = self._perform_gh_request('GET', '/repos/{}/{}/contents/{}?ref=master'.
                                               format(local_owner, repo, path), retry_until_status=200)

        obj_in_fork = obj_in_fork.json()

        last_sha = obj_in_fork['sha']

        content = base64.standard_b64decode(obj_in_fork['content'])

        if content == updated_content:
            print('Update already applied in fork for {}'.format(repo_full_name))
            return

        self._perform_gh_request('PUT', '/repos/{}/{}/contents/{}'.format(local_owner, repo, path),
                                 data=json.dumps(
                                     {'message': message, 'content': base64.standard_b64encode(updated_content),
                                      'sha': last_sha, 'branch': 'master'}), retry_until_status=200)

        self._perform_gh_request('POST', '/repos/' + repo_full_name + '/pulls',
                                 data=json.dumps({'title': message, 'head': local_owner + ':master', 'base': 'master'}))

    def _perform_gh_request(self, method, path, data=None, ok_status=[], retry_until_status=None):
        max_retries = 10
        for i in range(1, max_retries + 1):
            response = self.session.request(method, self.GH_API_BASE_URL + path, data=data)
            print('Github API Call: {} {} [{}]'.format(
                method, path, response.status_code))
            print('Github response: {}'.format(response.text))
            if not retry_until_status or retry_until_status == response.status_code:
                break
            else:
                print(
                    ('Re-trying request {} {} [{}] after sleeping for {} second(s)...'
                     .format(method, path, response.status_code, i)))
                time.sleep(i)
        if retry_until_status and retry_until_status != response.status_code:
            raise Exception("Could not get desired status after " + max_retries + " retries for {} {} [{}]".format(
                method, path, response.status_code))
        if response.status_code not in ok_status:
            response.raise_for_status()

        return response
