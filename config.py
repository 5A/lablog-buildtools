# -*- coding: utf-8 -*-

"""config.py:
This module defines the data model of config file.
It also provides methods to load config from config file, or dump config to a file.
"""

__author__ = "Zhi Zi"
__email__ = "x@zzi.io"
__version__ = "20231115"

# std libs
import os
import json
# third party libs
from pydantic import BaseModel

# meta params and defaults
CONFIG_PATH = os.path.join(os.path.dirname(__file__), './config.json')


class RESTfulConfig(BaseModel):
    protocol: str
    host: str
    port: int
    endpoint: str


class AuthConfig(BaseModel):
    username: str
    password: str
    access_token: str
    token_type: str
    force_reauthentication: bool  # whether to reauthenticate everytime the API loads


class APIConfig(BaseModel):
    restful: RESTfulConfig
    authentication: AuthConfig


class BuildPathConfig(BaseModel):
    # the buildtools will use this directory to store temporary outputs and logs
    # files in this directory will be deleted when script starts, so be aware
    temporary_files_directory: str
    # the template HTML file used to generate final HTML file
    post_template_file: str
    # where to find input posts
    posts_input_directory: str
    # where to export build results
    posts_output_directory: str
    # where to copy static files (images, attachments, etc.) to
    static_files_output_directory: str
    # a sitemap.txt is generated, which contains links to all built posts.
    sitemap_output_file: str
    # the typical situation is that user requests for all posts information,
    # for example when user accesses homepage.
    # thus this file can be buffered to reduce backend pressure. 
    buffered_posts_json_file: str
    # after generating html files, it still needs to be built with postcss, tailwind, etc.
    # this is the working directory where you typically run npm build
    npm_build_working_directory: str
    # output dir of npm build, buildtools will copy content of this dir to remote server
    frontend_dist_files: str
    # where to put the files on remote server (web root of nginx)
    remote_html_directory: str
    # link location embedded in the generated HTML file for creating and getting comments.
    comment_API_base_location: str
    # link location used to generate permenant links for the post, 
    # to be used in places like sitemap.txt, share buttons, etc.
    posts_web_root_location: str


class BuildConfig(BaseModel):
    api: APIConfig
    paths: BuildPathConfig


def load_config_from_file(config_path: str = CONFIG_PATH):
    with open(config_path, 'r') as f:
        r = json.load(f)
    return BuildConfig(**r)


def dump_config_to_file(config: BuildConfig, config_path: str = CONFIG_PATH):
    with open(config_path, 'w+') as f:
        f.write(config.model_dump_json(indent=2))


config = load_config_from_file()
