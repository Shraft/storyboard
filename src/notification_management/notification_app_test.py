from notification_app import app

client = app.test_client()

def test_get_notifications():
    response = client.get('/api/notifications')
    assert response.status_code == 200
