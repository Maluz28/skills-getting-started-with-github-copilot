# Tests for FastAPI Activities API

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test to ensure test isolation"""
    global activities
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Test the root endpoint"""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static index"""
        response = client.get("/")
        assert response.status_code == 307  # Temporary redirect
        assert "static/index.html" in response.headers["location"]


class TestActivitiesEndpoint:
    """Test the /activities endpoint"""

    def test_get_activities_success(self, client):
        """Test successful retrieval of all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 3  # Three activities
        
        # Check structure of first activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_get_activities_data_integrity(self, client):
        """Test that activities data is returned correctly"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert chess_club["description"] == "Learn strategies and compete in chess tournaments"
        assert chess_club["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
        assert chess_club["max_participants"] == 12
        assert chess_club["participants"] == ["michael@mergington.edu", "daniel@mergington.edu"]


class TestSignupEndpoint:
    """Test the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post("/activities/Chess%20Club/signup?email=newstudent@mergington.edu")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Signed up newstudent@mergington.edu for Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_signup_already_enrolled(self, client):
        """Test signup when student is already enrolled"""
        # First signup
        client.post("/activities/Chess%20Club/signup?email=duplicate@mergington.edu")
        
        # Try to signup again
        response = client.post("/activities/Chess%20Club/signup?email=duplicate@mergington.edu")
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"] == "Student is already signed up for this activity"

    def test_signup_activity_full(self, client):
        """Test signup when activity is at maximum capacity"""
        # Fill up Programming Class (max 20, currently has 2)
        for i in range(18):
            email = f"student{i}@mergington.edu"
            client.post(f"/activities/Programming%20Class/signup?email={email}")
        
        # Try to add one more (should be at capacity)
        response = client.post("/activities/Programming%20Class/signup?email=laststudent@mergington.edu")
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"] == "Activity is full"


class TestRemoveEndpoint:
    """Test the DELETE /activities/{activity_name}/signup endpoint"""

    def test_remove_success(self, client):
        """Test successful removal from an activity"""
        # First verify participant exists
        activities_response = client.get("/activities")
        initial_participants = activities_response.json()["Chess Club"]["participants"]
        assert "michael@mergington.edu" in initial_participants
        
        # Remove participant
        response = client.delete("/activities/Chess%20Club/signup?email=michael@mergington.edu")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Removed michael@mergington.edu from Chess Club" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        final_participants = activities_response.json()["Chess Club"]["participants"]
        assert "michael@mergington.edu" not in final_participants

    def test_remove_activity_not_found(self, client):
        """Test removal from non-existent activity"""
        response = client.delete("/activities/NonExistent/signup?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_remove_student_not_enrolled(self, client):
        """Test removal when student is not enrolled"""
        response = client.delete("/activities/Chess%20Club/signup?email=notenrolled@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Student not signed up for this activity"


class TestDataConsistency:
    """Test data consistency across operations"""

    def test_signup_remove_cycle(self, client):
        """Test that signup and remove operations maintain data consistency"""
        email = "cycle@mergington.edu"
        activity = "Gym Class"
        
        # Initial state
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Signup
        client.post(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
        signup_response = client.get("/activities")
        signup_count = len(signup_response.json()[activity]["participants"])
        assert signup_count == initial_count + 1
        assert email in signup_response.json()[activity]["participants"]
        
        # Remove
        client.delete(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
        remove_response = client.get("/activities")
        remove_count = len(remove_response.json()[activity]["participants"])
        assert remove_count == initial_count
        assert email not in remove_response.json()[activity]["participants"]

    def test_multiple_operations(self, client):
        """Test multiple signup/remove operations"""
        activity = "Programming Class"
        emails = ["multi1@mergington.edu", "multi2@mergington.edu", "multi3@mergington.edu"]
        
        # Add multiple participants
        for email in emails:
            client.post(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
        
        # Verify all were added
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in emails:
            assert email in participants
        
        # Remove all added participants
        for email in emails:
            client.delete(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
        
        # Verify all were removed
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in emails:
            assert email not in participants