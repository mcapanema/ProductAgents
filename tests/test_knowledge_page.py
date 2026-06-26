"""Page slices a matched list and reports paging metadata."""

from productagents.knowledge.services._page import Page


def test_paginate_slices_window_and_reports_total():
    page = Page.paginate(list(range(10)), limit=3, offset=3)
    assert page.items == [3, 4, 5]
    assert page.total == 10
    assert page.limit == 3
    assert page.offset == 3
    assert page.has_more is True


def test_has_more_is_false_on_the_last_page():
    page = Page.paginate([1, 2, 3], limit=10, offset=0)
    assert page.items == [1, 2, 3]
    assert page.total == 3
    assert page.has_more is False


def test_paginate_past_the_end_yields_empty_page():
    page = Page.paginate([1, 2, 3], limit=5, offset=10)
    assert page.items == []
    assert page.total == 3
    assert page.has_more is False
