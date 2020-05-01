# -*- coding: utf-8 -*-
"""Filter to limit lektor dependency generation by filtered queries.

"""
from base64 import (
    urlsafe_b64decode,
    urlsafe_b64encode,
    )
import binascii
import copy
import hashlib
from operator import itemgetter
import pickle

import jinja2
from lektor.context import get_ctx
from lektor.db import Query
from lektor.pluginsystem import Plugin
from lektor.sourceobj import VirtualSourceObject
from werkzeug.utils import cached_property

from lektorlib.context import disable_dependency_recording
from lektorlib.query import PrecomputedQuery
from lektorlib.recordcache import get_or_create_virtual


VIRTUAL_PATH_PREFIX = 'limit-dependencies'


class QueryResults(VirtualSourceObject):
    def __init__(self, query, id_):
        with disable_dependency_recording():
            root = query.pad.root
        super(QueryResults, self).__init__(root)
        self.query = query
        self._id = id_

    @cached_property
    def path(self):
        return "/@{}/{}".format(VIRTUAL_PATH_PREFIX, self._id)

    def get_checksum(self, path_cache):
        return _compute_checksum(self.query_result_ids)

    @cached_property
    def query_result_ids(self):
        with disable_dependency_recording():
            return tuple(map(itemgetter('_id'), self.query))


def _compute_checksum(data):
    return hashlib.sha1(pickle.dumps(data, protocol=0)).hexdigest()


def resolve_virtual_path(record, pieces):
    pad = record.pad
    if len(pieces) == 1 and record == pad.root:
        def creator():
            query = deserialize_query(pad, pieces[0])
            if query is not None:
                return QueryResults(query, id_=pieces[0])
        virtual_path = '{}/{}'.format(VIRTUAL_PATH_PREFIX, pieces[0])
        return get_or_create_virtual(pad.root, virtual_path, creator)


def serialize_query(query):
    # FIXME: put lektor version and/or plugin version into serialization?
    # (And fail deserialization on version mismatch.)

    # NB: this serialization is not stable, in the sense that
    # equivalent queries can serialize to different values (though
    # either serialization will still deserialize to an equivalent
    # query.)  It has to do with the ordering of the object __dict__ keys
    # in the pickle being non-deterministic.  (So far this issue has
    # only been observed in py35.)
    clone = copy.copy(query)
    clone.pad = None
    return urlsafe_b64encode(pickle.dumps(clone)).decode('ascii')


def deserialize_query(pad, serialized_query):
    # FIXME: log warnings on deserialization failures
    try:
        encoded = serialized_query.encode('ascii')
        query = pickle.loads(urlsafe_b64decode(encoded))
    except (binascii.Error, TypeError, pickle.UnpicklingError):
        return None
    if not isinstance(query, Query):
        return None
    query.pad = pad
    return query


@jinja2.environmentfilter
def limit_dependencies(jinja_env, query):
    if not isinstance(query, Query):
        return jinja_env.undefined(
            "limit_dependencies expected a Query instance, not {!r}"
            .format(query))

    # XXX: We cache the query results in the pad's record cache, so
    # any changes in the query results will not be noticed for the
    # lifetime of the pad.
    #
    # ``Lektor.devserver.BackgroundBuilder`` appears to create
    # a new pad for every rebuild attempt, and so any changes
    # in query results should get notice at the next rebuild
    # when running under ``lektor server``.
    id_ = serialize_query(query)

    def creator():
        return QueryResults(query, id_)
    with disable_dependency_recording():
        root = query.pad.root
    virtual_path = '{}/{}'.format(VIRTUAL_PATH_PREFIX, id_)
    results = get_or_create_virtual(root, virtual_path, creator)

    ctx = get_ctx()
    if ctx is not None:
        ctx.record_virtual_dependency(results)

    return PrecomputedQuery(query.path, query.pad, results.query_result_ids,
                            alt=query.alt)


class LimitDependenciesPlugin(Plugin):
    name = 'Limit Dependencies'
    description = u'Lektor plugin to limit dependencies created by queries.'

    def on_setup_env(self, **extra):
        env = self.env

        env.jinja_env.filters['limit_dependencies'] = limit_dependencies

        env.virtualpathresolver(VIRTUAL_PATH_PREFIX)(resolve_virtual_path)
