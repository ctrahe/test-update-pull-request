#!/usr/env/python

from botocore.vendored import requests
import time
import base64
import json
import kms
import os

GH_API_BASE_URL = 'https://api.github.com'

class GithubHandler(object):

    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers.update({'Authorization': 'token {}'.format(token)})
        self.org = self.get_whoami()

    def perform_file_update_with_pull_request(self, target_org, repo, branch, path, updated_content, message):
        self.delete_repo(repo)
        self.fork_repo(target_org, repo)

        file_obj = self.get_file_object(self.org, repo, 'mapping.yaml', branch)
        content = base64.standard_b64decode(file_obj['content'])
        if content == updated_content:
            print('Update already applied in fork for {}/{}'.format(target_org, repo))
            return

        updated_content = base64.standard_b64encode(updated_content.encode('utf-8'))
        self.commit_file(repo, path, branch, message, updated_content, file_obj['sha'])
        response = self.create_pull_request(target_org, repo, branch, branch, message)
        return json.loads(response.text)['html_url']

    def get_whoami(self):
        return self._perform_gh_request('GET', '/user').json()['login']

    def delete_repo(self, repo):
        self._perform_gh_request('DELETE', '/repos/{}/{}'.format(self.org, repo), ok_status=[404])

    def fork_repo(self, remote_org, remote_repo):
        self._perform_gh_request('POST', '/repos/{}/{}/forks'.format(remote_org, remote_repo))

    def create_pull_request(self, org, repo, source_branch, branch, message):
        return self._perform_gh_request('POST', '/repos/{}/{}/pulls'.format(org, repo),
                                        data=json.dumps({
                                         'title': message,
                                         'head': self.get_whoami() + ':' + source_branch,
                                         'base': branch}))

    def get_contents_of_file(self, org, repo, path, branch):
        response = self.get_file_object(org, repo, path, branch)
        return base64.decodebytes(response.content)['content'].encode()

    def get_file_object(self, org, repo, path, branch):
        return self._perform_gh_request('GET',
                                        '/repos/{}/{}/contents/{}?ref={}'.format(
                                            org, repo, path, branch)).json()

    def commit_file(self, repo, path, branch, message, updated_content, last_sha):
        self._perform_gh_request('PUT', '/repos/{}/{}/contents/{}'.format(self.org, repo, path),
                                 data=json.dumps(
                                     {'message': message, 'content': updated_content.decode(),
                                      'sha': last_sha, 'branch': branch}), retry_until_status=200)

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
