"""Test Job Description routes."""

def test_create_jd(client):
    """Test creating a job description."""
    jd_data = {
        "title": "Software Engineer",
        "description": "We are looking for a skilled software engineer.",
        "department": "Engineering",
        "location": "Remote",
        "employment_type": "Full-time",
        "min_experience": 2,
        "max_experience": 5,
        "min_salary": 80000,
        "max_salary": 120000,
        "required_skills": "Python, JavaScript, SQL"
    }
    
    response = client.post("/api/jds/", json=jd_data)
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["title"] == jd_data["title"]
    assert data["description"] == jd_data["description"]
    assert data["id"] is not None
    
    return data


def test_get_jd(client):
    """Test retrieving a job description."""
    # First create a JD
    jd_data = {
        "title": "Data Scientist",
        "description": "Looking for a data scientist.",
    }
    
    create_response = client.post("/api/jds/", json=jd_data)
    jd_id = create_response.json()["id"]
    
    # Now retrieve it
    response = client.get(f"/api/jds/{jd_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == jd_id
    assert data["title"] == jd_data["title"]


def test_list_jds(client):
    """Test listing all job descriptions."""
    # Create a couple of JDs
    client.post("/api/jds/", json={
        "title": "Frontend Developer",
        "description": "Frontend developer needed."
    })
    
    client.post("/api/jds/", json={
        "title": "Backend Developer",
        "description": "Backend developer needed."
    })
    
    # List all JDs
    response = client.get("/api/jds/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) >= 2


def test_update_jd(client):
    """Test updating a job description."""
    # First create a JD
    jd_data = {
        "title": "Original Title",
        "description": "Original description.",
    }
    
    create_response = client.post("/api/jds/", json=jd_data)
    jd_id = create_response.json()["id"]
    
    # Now update it
    update_data = {
        "title": "Updated Title",
        "description": "Updated description."
    }
    
    response = client.put(f"/api/jds/{jd_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]


def test_delete_jd(client):
    """Test deleting a job description."""
    # First create a JD
    jd_data = {
        "title": "To Be Deleted",
        "description": "This will be deleted.",
    }
    
    create_response = client.post("/api/jds/", json=jd_data)
    jd_id = create_response.json()["id"]
    
    # Now delete it
    response = client.delete(f"/api/jds/{jd_id}")
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/jds/{jd_id}")
    assert get_response.status_code == 404