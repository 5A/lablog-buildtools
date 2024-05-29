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
    post_template_file: str
    posts_input_directory: str
    posts_output_directory: str
    sitemap_output_file: str
    buffered_posts_json_file: str
    npm_build_working_directory: str


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
