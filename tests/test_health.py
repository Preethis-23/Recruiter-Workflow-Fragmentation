"""Test health check endpoint."""

def test_health_check(client):
    """Test that the health check endpoint returns expected response."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "environment" in data