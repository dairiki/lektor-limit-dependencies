# Lektor Limit Dependencies

[![PyPI version](https://img.shields.io/pypi/v/lektor-limit-dependencies.svg)](https://pypi.org/project/lektor-limit-dependencies/)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/lektor-limit-dependencies.svg)](https://pypi.python.org/pypi/lektor-limit-dependencies/)
[![GitHub license](https://img.shields.io/github/license/dairiki/lektor-limit-dependencies)](https://github.com/dairiki/lektor-limit-dependencies/blob/master/LICENSE)
[![GitHub Actions (Tests)](https://github.com/dairiki/lektor-limit-dependencies/workflows/Tests/badge.svg)](https://github.com/dairiki/lektor-limit-dependencies)


This is an experimental [Lektor][] plugin which aims to provide tools (or,
at least, a tool) to help keep Lektor’s dependency tracking under
control.

[lektor]: <https://www.getlektor.com/>


## Introduction

### Motivating Example

Suppose that you would like to list the three most recent blog posts
in the sidebar of your Lektor-based site.  This can be done by adding
something like to your site base template:

```html+jinja
<h3>Recent Posts</h3>
<ul>
  {% for post in site.query('/blog').order_by('-pub_date').limit(3) %}
    <li><a href="{{ post|url }}">{{ post.title }}</a></li>
  {% endfor %}
</ul>
```

This is not without drawbacks, however.  To sort the post query by
date, Lektor iterates through ***all*** of the blogs posts, then sorts
them.  In so doing, it records all of the blog posts as dependencies
*of every page on which this most-recent-post query is used*.  If this
is in the sidebar of every page on your site, *now every page on your
site will be rebuilt whenever any blog post at all* (not just one of
the three most recent posts) *is edited*.

Technically, it is true that all pages now depend on all posts.  You
might well edit the `pub_date` of one of your older posts, such that
it should now appear in the most-recent listing.  However, it is not
true that all pages need to be rebuilt for *any* edit of any post.
Unfortunately, Lektor’s dependency tracking system is not elaborate
enough to be able to express details about *how* pages are
dependendent on other pages; it only records that they *are*
dependent, so Lektor has no option but to rebuild everything.

### A Solution?

This plugin introduces a Jinja filter, `limit_dependencies`.  It
expects, as input, a Lektor query instance.  It iterates through the
input query, and returns a new query instance which will yield the
same results.  While it is doing its iteration, it, essentially,
monkey-patches Lektor’s dependency tracking machinery to prevent it
from recording any dependencies.

At the end, `limit_dependencies` records one dependency on a [virtual
source object][virtual] which depends only on the sequence of the identities
of the records in the query result.  (Lektor provides a means by which
virtual source objects can report checksums.  If they do, the
dependency tracking mechanism records those checksums, and will
trigger a rebuild should the checksum change.  `Limit_dependencies`
generates a virtual source object whose checksum depends on the
sequence identities in the query result.)

In the above example, this is exactly what we want.  We only want to
trigger a rebuild if the order or composition of the most-recent three
posts changes.  (Or if any of their titles change.  Note that this
gets covered, too, since when the resulting query is iterated over in
the `{% for %}` loop, dependencies will be recorded on the three
most-recent posts.)

Thus, the example above, if replaced by:

```html+jinja
<h3>Recent Posts</h3>
<ul>
  {% for post in site.query('/blog').order_by('-pub_date').limit(3)|limit_dependencies %}
    <li><a href="{{ post|url }}">{{ post.title }}</a></li>
  {% endfor %}
</ul>
```

will work in a much more efficient and sane manner.  Pages will be
rebuilt only if there are changes in the order, composition or content
of the three most recent posts.


[virtual]: <https://www.getlektor.com/docs/api/db/obj/#virtual-source-objects>
    "Lektor documentation on Virtual Source Objects"

## Installation

Add lektor-limit-dependencies to your project from command line:

```
lektor plugins add lektor-limit-dependencies
```

See [the Lektor plugin documentation][plugins] for more information.

[plugins]: <https://www.getlektor.com/docs/plugins/>

## Author

Jeff Dairiki <dairiki@dairiki.org>
