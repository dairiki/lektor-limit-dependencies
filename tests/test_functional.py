# -*- coding: utf-8 -*-
import shutil

import pytest
from six import text_type

from lektor.builder import Builder
from lektor.db import Database
from lektor.reporter import BufferReporter

from lektor_limit_dependencies import LimitDependenciesPlugin


@pytest.fixture
def site_path(site_path, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp('test-site')
    tmp_site_path = tmp_path / 'site'
    shutil.copytree(text_type(site_path), text_type(tmp_site_path))
    return tmp_site_path


@pytest.fixture
def touch_content(site_path):
    def touch_content(path):
        contents_lr = site_path / 'content' / path.lstrip('/') / 'contents.lr'
        assert contents_lr.is_file()
        with contents_lr.open(mode='at') as f:
            f.write(u"\n")
    return touch_content


@pytest.fixture
def lektor_env(lektor_env):
    # Load our plugin
    lektor_env.plugin_controller.instanciate_plugin(
        'limit-dependencies', LimitDependenciesPlugin)
    lektor_env.plugin_controller.emit('setup-env')
    return lektor_env


@pytest.fixture
def build_all(lektor_env, tmp_path_factory):
    db = Database(lektor_env)
    output_path = tmp_path_factory.mktemp('output')

    def build_all():
        builder = Builder(db.new_pad(), text_type(output_path))
        return builder.build_all()
    return build_all


@pytest.fixture
def reporter():
    with BufferReporter(lektor_env) as reporter:
        try:
            yield reporter
        finally:
            for failure in reporter.get_failures():
                pytest.fail(repr(failure))


@pytest.fixture
def get_built_artifact_names(reporter):
    def get_built_artifact_names(include_current=False):
        built = set()
        for event, data in reporter.buffer:
            if event == 'start-artifact-build':
                if include_current or not data['is_current']:
                    built.add(data['artifact'].artifact_name)
        return built
    return get_built_artifact_names


class Reporter(BufferReporter):
    def __exit__(self, type_, value, tb):
        self.assert_no_failures()

    def assert_no_failures(self):
        for failure in self.get_failures():
            pytest.fail(repr(failure))

    def get_built_artifact_names(self, include_current=False):
        built = set()
        for event, data in self.buffer:
            if event == 'start-artifact-build':
                if include_current or not data['is_current']:
                    built.add(data['artifact'].artifact_name)
        return built

    def report_dependencies(self, dependencies):
        artifact = self.current_artifact
        for dep in dependencies:
            print("DEPS {}: {}".format(
                artifact.source_obj.path, dep.source[:30]))

    def report_failure(self, artifact, exc_info):
        artifact = self.current_artifact
        print("BUILD FAILURE {}: {}".format(
            artifact.artifact_name, exc_info[1]))


class TestFunctional(object):

    @pytest.fixture
    def built_site(self, lektor_env, build_all):
        with Reporter(lektor_env) as reporter:
            build_all()
        assert reporter.get_built_artifact_names() == {
            'index.html',
            'about/index.html',
            'projects/index.html',
            'static/style.css',
            }

    @pytest.mark.usefixtures('built_site')
    def test_editing_about_rebuilds_all(self, lektor_env,
                                        build_all, touch_content):
        # test-site/templates/layout.html includes a link to the first child
        # of the root record.  That is /about.  Since /about is included on
        # every page, dditing /about will cause all pages to rebuild.
        touch_content('about')

        with Reporter(lektor_env) as reporter:
            build_all()
        assert reporter.get_built_artifact_names() == {
            'index.html',
            'about/index.html',
            'projects/index.html',
            }

    @pytest.mark.usefixtures('built_site')
    def test_editing_projects_does_not_rebuild_all(self, lektor_env,
                                                   build_all, touch_content):
        # test-site/templates/layout.html includes a link to the first child
        # of the root record.  That is /about.
        #
        # It finds the first child by doing:
        #
        # site.root.children.limit(1)|limit-dependencies
        #
        # Because of the use of limit-dependencies, changing the second child,
        # /projects, should not cause a whole site rebuild.
        #
        touch_content('projects')
        with Reporter(lektor_env) as reporter:
            build_all()
        assert reporter.get_built_artifact_names() == {
            'projects/index.html',
            }
