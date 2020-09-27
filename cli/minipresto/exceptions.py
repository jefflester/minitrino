#!usr/bin/env/python3
# -*- coding: utf-8 -*-

class MiniprestoException(Exception):
    """An exception that Minipresto can handle and show to the user."""

    exit_code = 1

    def __init__(self, msg=""):
        super().__init__(msg)
        self.msg = msg

    def __str__(self):
        return self.msg
