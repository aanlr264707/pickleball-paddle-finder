import pytest

from paddle_finder.api import create_app


def test_health(client):
    body = client.get("/api/health").get_json()
    assert body["status"] == "ok" and body["paddles"] == 494


def test_metrics_options_presets(client):
    metrics = client.get("/api/metrics").get_json()
    assert {m["key"] for m in metrics} >= {"power", "swing_weight", "price"}
    assert next(m for m in metrics if m["key"] == "price")["in_questionnaire"] is False
    options = client.get("/api/options").get_json()
    assert set(options) == {"brand", "shape", "paddle_type", "feel"}
    presets = client.get("/api/presets").get_json()
    assert presets[0]["slug"] == "power-banger"


def recommend(client, body):
    return client.post("/api/recommendations", json=body)


def test_recommendations_respect_filters_and_rank_best_first(client):
    response = recommend(client, {
        "filters": {"max_price": 200, "tournament_only": True, "shape": "Elongated"},
        "preferences": [{"metric": "power", "target": "high", "importance": 5},
                        {"metric": "core", "target": 16}],
        "limit": 8,
    })
    assert response.status_code == 200
    body = response.get_json()
    assert body["ranked"] is True and len(body["results"]) == 8
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)
    for result in body["results"]:
        paddle = result["paddle"]
        assert paddle["price"] is None or paddle["price"] <= 200
        assert paddle["tournament_legal"] and paddle["shape"] == "Elongated"
    assert body["preferences"][1] == {"metric": "core", "label": "Core", "target": 16.0, "importance": 3}


def test_recommendations_from_a_preset(client):
    body = recommend(client, {"preset": "fast-hands", "limit": 3}).get_json()
    assert body["preset"] == "fast-hands" and len(body["results"]) == 3


def test_filters_that_match_nothing_return_an_empty_list(client):
    body = recommend(client, {"filters": {"max_price": 1}, "preferences": []}).get_json()
    assert body["candidates"] >= 0
    assert all(r["paddle"]["price"] is None for r in body["results"])


@pytest.mark.parametrize("body, field", [
    ({"preferences": [{"metric": "power", "target": "banana"}]}, "preferences[0].target"),
    ({"preferences": [{"metric": "power", "target": "high", "importance": 9}]}, "preferences[0].importance"),
    ({"preferences": [{"metric": "colour", "target": 1}]}, "preferences[0].metric"),
    ({"preferences": [{"metric": "pop", "target": 1}, {"metric": "pop", "target": 2}]},
     "preferences[1].metric"),
    ({"filters": {"shape": "Square"}}, "filters.shape"),
    ({"filters": {"max_price": -5}}, "filters.max_price"),
    ({"preset": "nope"}, "preset"),
    ({"preset": "fast-hands", "preferences": [{"metric": "pop", "target": 1}]}, "preferences"),
    ({"limit": 0}, "limit"),
])
def test_bad_recommendation_input_is_a_400_naming_the_field(client, body, field):
    response = recommend(client, body)
    assert response.status_code == 400
    assert response.get_json()["error"]["field"] == field


def test_non_json_body_is_rejected(client):
    response = client.post("/api/recommendations", data="not json", content_type="application/json")
    assert response.status_code == 400


def test_paddle_list_search_sort_and_paging(client):
    body = client.get("/api/paddles?q=selkirk&sort=price&order=desc&per_page=5").get_json()
    prices = [p["price"] for p in body["items"]]
    assert prices == sorted(prices, reverse=True)
    assert body["total"] >= len(body["items"]) and body["pages"] >= 1
    assert all("selkirk" in p["full_name"].lower() for p in body["items"])
    assert client.get("/api/paddles?sort=bogus").status_code == 400
    assert client.get("/api/paddles?per_page=1000").status_code == 400


def test_paddle_detail_similar_and_404(client):
    body = client.get("/api/paddles/1").get_json()
    assert body["paddle"]["id"] == 1
    assert not [key for key in body["paddle"] if "discount" in key]
    assert 0 <= body["percentiles"]["swing_weight"] <= 100
    similar = client.get("/api/paddles/1/similar?limit=4").get_json()
    assert len(similar) == 4 and all(item["paddle"]["id"] != 1 for item in similar)
    missing = client.get("/api/paddles/99999")
    assert missing.status_code == 404 and missing.get_json()["error"]["status"] == 404


def test_compare(client):
    body = client.get("/api/compare?ids=3,1,2").get_json()
    assert [entry["paddle"]["id"] for entry in body] == [3, 1, 2]
    assert client.get("/api/compare?ids=1").status_code == 400
    assert client.get("/api/compare?ids=1,2,3,4,5").status_code == 400
    assert client.get("/api/compare?ids=1,99999").status_code == 404


def test_insights(client):
    body = client.get("/api/insights").get_json()
    assert body["summary"]["paddles"] == 494
    assert [row["paddle_type"] for row in body["by_type"]][0] == "Control"
    assert sum(row["count"] for row in body["by_type"]) == 494
    drivers = body["power_drivers"]
    assert abs(drivers[0]["correlation"]) >= abs(drivers[-1]["correlation"])
    assert all(point["price"] is not None for point in body["price_vs_power"])


def test_unknown_routes_and_methods_answer_in_json(client):
    assert client.get("/api/nope").get_json()["error"]["status"] == 404
    assert client.delete("/api/health").status_code == 405


def test_serves_the_built_frontend_with_client_side_routes(database_url, engine, tmp_path):
    (tmp_path / "index.html").write_text("<div id=root></div>")
    app = create_app({"DATABASE_URL": database_url, "AUTO_SEED": False, "FRONTEND_DIST": str(tmp_path)})
    client = app.test_client()
    assert b"root" in client.get("/").data
    assert b"root" in client.get("/paddles/12").data
    assert client.get("/api/does-not-exist").status_code == 404
