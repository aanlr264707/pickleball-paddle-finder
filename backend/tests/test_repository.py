import pytest

from paddle_finder.core import filters
from paddle_finder.core.models import Filters
from paddle_finder.data import repository
from paddle_finder.data.repository import PaddleQuery

FILTER_CASES = [
    Filters(),
    Filters(max_price=180),
    Filters(tournament_only=True, shape="Elongated"),
    Filters(max_price=220, paddle_type="Power", feel="Soft/Dense"),
]


@pytest.mark.parametrize("paddle_filters", FILTER_CASES)
def test_sql_filtering_matches_the_python_engine(engine, catalog, paddle_filters):
    with engine.connect() as conn:
        sql_ids = repository.candidate_ids(conn, paddle_filters)
    python_ids = [p.id for p in filters.filter_paddles(catalog.paddles, paddle_filters)]
    assert sql_ids == python_ids


def search(engine, **kwargs):
    with engine.connect() as conn:
        return repository.search_paddle_ids(conn, PaddleQuery(**kwargs))


def test_text_search_is_case_insensitive_and_needs_every_word(engine, catalog):
    ids, total = search(engine, text="joola PERSEUS", per_page=100)
    assert total == len(ids) > 0
    for paddle in catalog.many(ids):
        assert "joola" in paddle.full_name.lower() and "perseus" in paddle.full_name.lower()


def test_like_wildcards_are_matched_literally(engine):
    assert search(engine, text="%")[1] == 0
    assert search(engine, text="_")[1] == 0


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_sorting_puts_missing_values_last(engine, catalog, order):
    ids, total = search(engine, sort="spin", order=order, per_page=100, page=5)
    values = [p.spin for p in catalog.many(ids)]
    known = [v for v in values if v is not None]
    assert values[:len(known)] == known                         # all None at the end
    assert known == sorted(known, reverse=(order == "desc"))


def test_pages_do_not_overlap_and_cover_everything(engine):
    seen = []
    for page in range(1, 22):
        ids, total = search(engine, sort="price", per_page=24, page=page)
        seen.extend(ids)
    assert total == 494
    assert sorted(seen) == list(range(1, 495))


def test_bad_sort_breaks_a_precondition(engine):
    with pytest.raises(AssertionError):
        search(engine, sort="drop table")
