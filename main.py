#!/usr/env/python

import githubhandler


repo_full_name = "lucioveloso/test-update-pull-request"
path = "test.txt"
updated_content = 'b b b b'
message = 'Pull Request Message'

githubhandler.perform_file_update_with_pull_request(repo_full_name, path, updated_content, message)
