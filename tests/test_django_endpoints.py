import os
import pytest
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruiter_project.settings')
django.setup()

@pytest.fixture
def django_client():
    return Client()

def test_django_health(django_client):
    response = django_client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'recruiter-workflow-fragmentation'

def test_django_index(django_client):
    response = django_client.get('/')
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']

def test_django_jds_crud(django_client):
    # 1. Create JD
    jd_payload = {
        "title": "Django Senior Architect",
        "description": "Design and build scalable distributed recruitment systems.",
        "department": "Engineering",
        "location": "San Francisco / Remote",
        "employment_type": "Full-time",
        "required_skills": "Python, Django, PostgreSQL, Celery, Redis"
    }
    create_res = django_client.post('/api/jds/', data=jd_payload, content_type='application/json')
    assert create_res.status_code == 201
    jd = create_res.json()
    jd_id = jd['id']
    assert jd['title'] == jd_payload['title']

    # 2. Get JD
    get_res = django_client.get(f'/api/jds/{jd_id}')
    assert get_res.status_code == 200
    assert get_res.json()['id'] == jd_id

    # 3. List JDs
    list_res = django_client.get('/api/jds/')
    assert list_res.status_code == 200
    assert any(j['id'] == jd_id for j in list_res.json())

    # 4. Update JD
    update_res = django_client.put(
        f'/api/jds/{jd_id}',
        data={"description": "Updated Django architecture requirements"},
        content_type='application/json'
    )
    assert update_res.status_code == 200
    assert update_res.json()['description'] == "Updated Django architecture requirements"

    # 5. Delete JD
    del_res = django_client.delete(f'/api/jds/{jd_id}')
    assert del_res.status_code == 204

def test_django_agent_tools(django_client):
    response = django_client.get('/api/agent/tools')
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert data["total_tools"] > 0
