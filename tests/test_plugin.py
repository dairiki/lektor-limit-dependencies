# -*- coding: utf-8 -*-
from base64 import urlsafe_b64encode
import pickle
import sys

import pytest
import six

import jinja2
from lektor.environment import Expression

from lektorlib.testing import assert_no_dependencies

from lektor_limit_dependencies import (
    VIRTUAL_PATH_PREFIX,
    QueryResults,
    _compute_checksum,
    resolve_virtual_path,
    serialize_query,
    deserialize_query,
    limit_dependencies,
    LimitDependenciesPlugin,
    )


@pytest.fixture(params=[
    ('this.children', ['about', 'projects']),
    ('this.children.filter(F._id < "g")', ['about']),
    ('this.children.order_by("-title")', ['projects', 'about']),
    ('this.children.order_by("title").limit(1)', ['about']),
    ('this.children.order_by("title").limit(1).offset(1)', ['projects']),
    ('this.children.filter(F.title == "missing")', []),
    ])
def _test_data(request):
    return request.param


@pytest.fixture
def query_expr(_test_data):
    return _test_data[0]


@pytest.fixture
def expected_result_ids(_test_data):
    return _test_data[1]


@pytest.fixture
def query(lektor_env, lektor_pad, query_expr):
    record = lektor_pad.root
    expr = Expression(lektor_env, query_expr)
    return expr.evaluate(lektor_pad, this=record, alt=record.alt)


def test_sanity(query, expected_result_ids):
    result_ids = tuple(obj['_id'] for obj in query)
    assert result_ids == tuple(expected_result_ids)


class TestQueryResults(object):
    @pytest.fixture
    def id_(self):
        return "query-id"

    @pytest.fixture
    def query_results(self, query, id_):
        return QueryResults(query, id_)

    def test_record(self, query_results, lektor_pad):
        assert query_results.record is lektor_pad.root

    def test_path(self, query_results, id_):
        assert query_results.path == "/@{}/{}".format(VIRTUAL_PATH_PREFIX, id_)

    def test_get_checksum(self, query_results):
        checksum = query_results.get_checksum(path_cache='ignored')
        assert checksum and isinstance(checksum, six.string_types)

    @pytest.mark.usefixtures('lektor_context')
    def test_query_result_ids(self, query_results, query, expected_result_ids):
        with assert_no_dependencies():
            result_ids = query_results.query_result_ids
        assert result_ids == tuple(expected_result_ids)


@pytest.mark.parametrize(('data', 'checksum'), [
    ((),
     "5d460934f4a194c28ce73ada3b56d2e025d5c47c"),
    ((u'a/b',),
     "224e70bd496625246063b11ffd5fab19e0fc763d"),
    ((u'a', u'b'),
     "ceb654484413126293abed9693ffe738220afcca"),
    ])
def test__compute_checksum(data, checksum):
    # These checksums should be portable across platforms
    assert _compute_checksum(data) == checksum


def assert_queries_equal(query, other_query):
    # ignore differences in pad
    def ignore_pad(query):
        d = query.__dict__
        d.pop('pad', None)
        return d
    assert query.__class__ is other_query.__class__
    assert ignore_pad(query) == ignore_pad(other_query)


class Test_resolve_virtual_path(object):
    def test_resolves(self, query, lektor_pad):
        record = lektor_pad.root
        id_ = serialize_query(query)
        query_results = resolve_virtual_path(record, [id_])
        assert_queries_equal(query, query_results.query)

    def test_uses_cache(self, query, lektor_pad, query_expr):
        record = lektor_pad.root
        id_ = serialize_query(query)
        query_results = resolve_virtual_path(record, [id_])
        assert query_results._id == id_
        # NB: the following is not always true (only noticed in py35, depending
        # on PYTHONHASHSEED)
        #
        # assert serialize_query(query_results.query) == id_
        assert resolve_virtual_path(record, [id_]) is query_results

        # try with new pad
        other_pad = lektor_pad.env.new_pad()
        other_query_results = resolve_virtual_path(other_pad.root, [id_])
        assert other_query_results is not query_results
        assert_queries_equal(query, other_query_results.query)

    def test_only_resolves_on_root(self, query, lektor_pad):
        record = lektor_pad.get('/about')
        id_ = serialize_query(query)
        assert resolve_virtual_path(record, [id_]) is None

    def test_extra_pieces(self, query, lektor_pad):
        record = lektor_pad.root
        id_ = serialize_query(query)
        assert resolve_virtual_path(record, [id_, 'extra']) is None

    @pytest.mark.parametrize('pieces', [
        [],
        ['bad-serialization'],
        ])
    def test_bad_virtual_path(self, query, pieces, lektor_pad):
        record = lektor_pad.root
        assert resolve_virtual_path(record, pieces) is None


def test_serialize_query(query, query_expr, lektor_env):
    serialized = serialize_query(query)
    assert isinstance(serialized, six.string_types)
    assert len(serialized) < 1024
    print("query {!r} => serialized to length {:d}"
          .format(query_expr, len(serialized)))


@pytest.mark.xfail(
    sys.version_info < (3, 6),
    reason="This fails sometimes due to non-determinstic ordering "
    "of object dict keys by pickle.dumps().")
def test_serialize_query_is_deterministic(query, query_expr, lektor_env):
    serialized = serialize_query(query)
    for n in range(10):
        new_pad = lektor_env.new_pad()
        q2 = deserialize_query(new_pad, serialized)
        assert serialize_query(q2) == serialized


class Test_deserialize_query(object):
    def test_deserialize_query(self, query, query_expr, lektor_env):
        new_pad = lektor_env.new_pad()
        query_clone = deserialize_query(new_pad, serialize_query(query))
        assert [record.path for record in query_clone] \
            == [record.path for record in query]

    @pytest.fixture
    def serialized_nonquery(self):
        nonquery = object()
        return urlsafe_b64encode(pickle.dumps(nonquery)).decode('ascii')

    def test_deserialize_nonquery(self, lektor_pad, serialized_nonquery):
        assert deserialize_query(lektor_pad, serialized_nonquery) is None


class Test_limit_dependencies(object):
    @pytest.mark.usefixtures('lektor_context')
    def test(self, jinja_env, query):
        with assert_no_dependencies(match=r'\A(?!.*@limit-dependencies).'):
            result = limit_dependencies(jinja_env, query)
        assert list(result) == list(query)

    def test_records_dependency(self, jinja_env, query, lektor_context):
        limit_dependencies(jinja_env, query)
        assert any(
            path.startswith('/@limit-dependencies/')
            for path in lektor_context.referenced_virtual_dependencies.keys())

    def test_returns_undefined(self, jinja_env):
        result = limit_dependencies(jinja_env, 'not a query')
        assert jinja2.is_undefined(result)


class TestLimitDependenciesPlugin(object):
    @pytest.fixture
    def plugin(self, lektor_env):
        return LimitDependenciesPlugin(lektor_env, 'limit-dependencies')

    def test_on_setup_env(self, plugin, lektor_env):
        jinja_filters = lektor_env.jinja_env.filters
        plugin.on_setup_env()

        assert jinja_filters['limit_dependencies'] is limit_dependencies
        assert lektor_env.virtual_sources[VIRTUAL_PATH_PREFIX] \
            == resolve_virtual_path
