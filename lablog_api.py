# -*- coding: utf-8 -*-

"""api.py:
Python API for lablog backend
"""

__author__ = "Zhi Zi"
__email__ = "x@zzi.io"
__version__ = "20240528"

# std libs
import logging
import json
import datetime
# third-party libs
import requests
import jwt
# this package
from config import load_config_from_file, dump_config_to_file

lg = logging.getLogger(__name__)


class LablogAPI():
    def __init__(self, config_path: str | None = None) -> None:
        lg.info("Reading config file.")
        if config_path is None:
            self.config = load_config_from_file()
        else:
            self.config = load_config_from_file(config_path=config_path)
        # load connection info
        cfg = self.config.api.restful
        self.restful_endpoint = "{protocol}{host}:{port}{endpoint}".format(
            protocol=cfg.protocol, host=cfg.host, port=cfg.port, endpoint=cfg.endpoint)
        self.auth_header = self.config.api.authentication.token_type + \
            " " + self.config.api.authentication.access_token
        # authentication
        lg.info("Checking authentication status")
        self.pending_reauthentication = self.check_reauthentication_required()
        lg.info("Reauthentication needed: {}".format(
            self.pending_reauthentication))
        if self.pending_reauthentication:
            lg.info("Authenticating client...")
            self.handle_reauthenticate()

    def check_reauthentication_required(self) -> bool:
        """
        Checks for JWT expiration and empty JWT locally.
        Note that this only verifies the basic token formats and time, it does not verify the signature.
        Use validate_token if a full remote validation is needed.
        """
        # check for empty access token
        if self.config.api.authentication.access_token == "":
            lg.info("Empty JWT, reauthentication is required.")
            return True
        # check for token basic format and expiration
        try:
            decoded = jwt.decode(
                self.config.api.authentication.access_token,
                options={"verify_signature": False})  # works in PyJWT >= v2.0
            tnow = datetime.datetime.now(tz=datetime.UTC)
            texp = datetime.datetime.fromtimestamp(
                decoded["exp"], tz=datetime.UTC)
            if (texp - tnow) < datetime.timedelta(seconds=30):
                lg.info("Reauthencitation is required before token expiration!")
                lg.info("Time now is {}".format(
                    tnow.strftime("%Y-%m-%d %H:%M:%S")))
                lg.info("Time to expire is {}".format(
                    texp.strftime("%Y-%m-%d %H:%M:%S")))
                # 30 seconds until expiration
                return True
        except jwt.exceptions.DecodeError as e:
            # malformed JWT, reauthenticate to correct it.
            lg.info(
                "Reauthentication required because local JWT cannot be decoded: {}".format(e))
            return True
        except KeyError as e:
            # no expiration time found in decoded token, it must be invalid.
            lg.info("Cannot fint {} field in JWT! Is this JWT correct?".format(e))
            return True
        return False

    def handle_reauthenticate(self) -> None:
        """
        Tries to authenticate this client, callback for the .authenticate method.
        This callback catches exceptions, so a outer loop is required for automatic retry.
        """
        try:
            self.authenticate()
        except AssertionError:
            lg.error(
                "Authentication failed, check the credentials provided in config.")
        except requests.exceptions.RequestException as e:
            lg.error(
                "Cannot access authentication service, check the connection status: {}".format(e))
        except Exception as e:
            lg.error(
                "Unexpected error occured during re-authentication. Error is {}".format(e))

    def authenticate(self) -> None:
        """
        Tries to authenticate this client using credentials provided in config.
        """
        lg.info("Authenticating client.")
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "username": self.config.api.authentication.username,
            "password": self.config.api.authentication.password
        }
        response = requests.post(self.restful_endpoint + "token",
                                 headers=headers,
                                 data=data)
        result = json.loads(response.content.decode())
        assert "access_token" in result
        lg.info("Successfully logged in, token type: {}".format(
            result["token_type"]))
        self.config.api.authentication.access_token = result["access_token"]
        self.config.api.authentication.token_type = result["token_type"]
        self.auth_header = result["token_type"] + " " + result["access_token"]
        dump_config_to_file(self.config)

    def get_posts(self):
        response = requests.get(self.restful_endpoint + "posts")
        result = json.loads(response.content.decode())
        return result

    def register_post(self, data: dict):
        headers = {
            "accept": "application/json",
            "Authorization": self.auth_header
        }
        response = requests.post(
            self.restful_endpoint + "posts", headers=headers, json=data)
        result = json.loads(response.content.decode())
        return result
