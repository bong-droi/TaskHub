import pytest

from app.schemas.common import Page
from tests.conftest import WS


@pytest.mark.parametrize(
    ("total", "limit", "pages"), [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2), (5, 2, 3)]
)
def test_pages_is_computed_from_total_and_limit(total, limit, pages):
    assert Page[int](items=[], total=total, page=1, limit=limit).pages == pages


async def test_page_is_one_based_and_validated(team, anon):
    url = f"{WS}?page=1&limit=1"
    body = (await anon.get(url, headers=team.h["alice"])).json()
    assert body["page"] == 1 and body["limit"] == 1 and body["pages"] == 1
    for bad in ("page=0", "page=-1", "limit=0", "limit=101", "page=abc"):
        assert (await anon.get(f"{WS}?{bad}", headers=team.h["alice"])).status_code == 422


async def test_page_beyond_last_returns_empty_items_with_total(team, anon):
    body = (await anon.get(f"{WS}?page=9", headers=team.h["alice"])).json()
    assert body["items"] == [] and body["total"] == 1
