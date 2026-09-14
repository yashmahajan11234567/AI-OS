#!/usr/bin/env python3

from aios.adapters.freellmapi import FreeLLMAPIConfig

config = FreeLLMAPIConfig(
    base_url="http://secret-server:8080",
    api_key="super-secret-key-12345",
    timeout_seconds=30,
    default_model="secret-model"
)

print("str(config):")
print(str(config))
print()
print("repr(config):")
print(repr(config))
print()
print("config.__dict__:")
print(config.__dict__)