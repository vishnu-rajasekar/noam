"""Namespace package for per-domain engineering code (Maxwell, Joule, ...).

This is distinct from the repository-root ``domains/`` directory, which
holds authored ``Capability``/``Precedent`` YAML records (data, reviewed and
promoted out of a study). This package holds the Python capabilities those
records can eventually point to. See ARCHITECTURE.md's domain boundary: a
package is added here only when a real study needs it, not ahead of need.
"""
