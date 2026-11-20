def test_home_page_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"AIHub" in r.data and b"/static/app.js" in r.data


def test_static_assets_served(client):
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
