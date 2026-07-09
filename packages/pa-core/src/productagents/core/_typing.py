"""Shared alias for the ``list`` builtin.

A class with a method literally named ``list`` shadows the builtin ``list``
name for annotations elsewhere in that class body (ty resolves them even
under ``from __future__ import annotations``). Import ``List`` here instead
of redefining a local ``_L = list`` alias in every affected module.
"""

List = list
