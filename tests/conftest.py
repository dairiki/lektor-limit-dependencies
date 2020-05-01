# -*- coding: utf-8 -*-

try:
    from pathlib import Path
except ImportError:
    # python < 3.4
    from pathlib2 import Path

import pytest
from six import text_type

import lektor.builder
import lektor.context
import lektor.datamodel
import lektor.db
import lektor.environment
import lektor.pagination
import lektor.project


@pytest.fixture(scope="session")
def site_path():
    return Path(__file__).parent / 'test-site'


@pytest.fixture
def lektor_project(site_path):
    return lektor.project.Project.from_path(text_type(site_path))


@pytest.fixture
def lektor_env(lektor_project):
    return lektor.environment.Environment(lektor_project, load_plugins=False)


@pytest.fixture
def lektor_pad(lektor_env):
    return lektor.db.Database(lektor_env).new_pad()


@pytest.fixture
def lektor_builder(lektor_pad, tmp_path):
    return lektor.builder.Builder(lektor_pad, tmp_path)


@pytest.fixture
def lektor_build_state(lektor_builder):
    with lektor_builder.new_build_state() as build_state:
        yield build_state


@pytest.fixture
def lektor_context(lektor_pad):
    with lektor.context.Context(pad=lektor_pad) as ctx:
        yield ctx


@pytest.fixture
def jinja_env(lektor_env):
    return lektor_env.jinja_env
