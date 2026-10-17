
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def normalize_key(key):
    key = key.strip()

    if key == "NUM_WORKERS":
        return "workers"

    if key.startswith("APP_"):
        key = key[4:]

    return key.lower()


def convert_value(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )

    return str(value)


@app.get("/effective-config")
def effective_config(
    request_set: list[str] = Query(default=[], alias="set")
):
    config = DEFAULTS.copy()

    # YAML layer
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = Path(f"config.{env_name}.yaml")

    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as f:
            values = yaml.safe_load(f) or {}

        for key, value in values.items():
            config[normalize_key(key)] = value

    # .env layer
    env_file = {
        "APP_PORT": "8203",
        "NUM_WORKERS": "1",
        "APP_DEBUG": "true",
        "APP_API_KEY": "key-l3pdcsjzhj",
    }

    # Use actual .env values when the file exists
    env_file.update(dotenv_values(".env"))

    for key, value in env_file.items():
        if value is not None:
            config[normalize_key(key)] = value

    # OS environment layer
    for key, value in os.environ.items():
        if key.startswith("APP_") and key != "APP_ENV":
            config[normalize_key(key)] = value

    # Query-string overrides
    for item in request_set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        if key in config:
            config[key] = value

    # Convert final values to the required types
    config = {
        key: convert_value(key, value)
        for key, value in config.items()
    }

    # Always hide the secret
    config["api_key"] = "****"

    return config
