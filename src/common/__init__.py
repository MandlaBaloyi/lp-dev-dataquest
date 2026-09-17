"""Shared foundations - the things every other package needs.

    paths.py    every file location, resolved once
    emis.py     the national school identifier and how to normalise it
    data.py     loading the panel

These live together because each was being reinvented in separate modules, and
small differences between copies cause silent damage. Two modules normalising
an identifier slightly differently produce joins that look successful and
quietly match fewer rows than they should.

paths.py in particular means a script can move between folders without
breaking. Each file computing the project root by walking up its own parents
fails the moment it is moved one directory deeper.
"""
