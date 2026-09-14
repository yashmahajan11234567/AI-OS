#!/usr/bin/env python3

import os
from unittest.mock import patch
from aios.adapters.freellmapi import get_freellmapi_config_from_env

print("Environment before:", dict(os.environ))

# Test with no env vars
with patch.dict(os.environ, {}, clear=True):
    print("Environment during patch:", dict(os.environ))
    config = get_freellmapi_config_from_env()
    print(f"Config: base_url='{config.base_url}', api_key='{config.api_key}'")
    print(f"Is base_url empty? {not config.base_url}")
    print(f"Is base_url localhost? {config.base_url == 'http://localhost:8080'}")