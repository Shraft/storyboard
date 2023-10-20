from user_app import app

app.testing = True
client = app.test_client()

def test_get_users():
    response = client.get('/api/users')
    assert response.status_code == 200

def test_get_user():
    response = client.get('/api/user/1')
    assert response.status_code == (200 or 404)

def test_get_tagged_users():
    response = client.get('/api/tagged_users/@user1@user2')
    assert response.status_code == 200

