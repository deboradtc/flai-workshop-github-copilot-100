"""
Tests for the Mergington High School API endpoints
"""
import pytest
from fastapi import status


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successful retrieval of all activities"""
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # Should have 9 activities
        
        # Verify some expected activities are present
        assert "Soccer Team" in data
        assert "Swimming Club" in data
        assert "Programming Class" in data
    
    def test_get_activities_returns_correct_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        # Check structure of Soccer Team
        soccer = data["Soccer Team"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert isinstance(soccer["participants"], list)
    
    def test_get_activities_returns_participants(self, client):
        """Test that activities include participant lists"""
        response = client.get("/activities")
        data = response.json()
        
        soccer = data["Soccer Team"]
        assert "lucas@mergington.edu" in soccer["participants"]
        assert "james@mergington.edu" in soccer["participants"]


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Soccer Team"
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Soccer Team"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_student_already_signed_up(self, client):
        """Test signup when student is already enrolled"""
        response = client.post(
            "/activities/Soccer Team/signup",
            params={"email": "lucas@mergington.edu"}  # Already enrolled
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_multiple_students(self, client):
        """Test multiple students can sign up for the same activity"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                "/activities/Chess Club/signup",
                params={"email": email}
            )
            assert response.status_code == status.HTTP_200_OK
        
        # Verify all students were added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        participants = activities["Chess Club"]["participants"]
        
        for email in emails:
            assert email in participants
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity names"""
        response = client.post(
            "/activities/Programming Class/signup",
            params={"email": "coder@mergington.edu"}
        )
        assert response.status_code == status.HTTP_200_OK


class TestUnregisterFromActivity:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        response = client.delete(
            "/activities/Soccer Team/unregister",
            params={"email": "lucas@mergington.edu"}
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Removed lucas@mergington.edu from Soccer Team"
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "lucas@mergington.edu" not in activities["Soccer Team"]["participants"]
    
    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_student_not_found(self, client):
        """Test unregister when student is not enrolled"""
        response = client.delete(
            "/activities/Soccer Team/unregister",
            params={"email": "notenrolled@mergington.edu"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Student not found" in response.json()["detail"]
    
    def test_unregister_all_participants(self, client):
        """Test removing all participants from an activity"""
        # Get initial participants
        activities_response = client.get("/activities")
        activities = activities_response.json()
        participants = activities["Chess Club"]["participants"].copy()
        
        # Remove all participants
        for email in participants:
            response = client.delete(
                "/activities/Chess Club/unregister",
                params={"email": email}
            )
            assert response.status_code == status.HTTP_200_OK
        
        # Verify activity has no participants
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert len(activities["Chess Club"]["participants"]) == 0


class TestActivityWorkflow:
    """Integration tests for complete activity workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow: signup then unregister"""
        email = "workflow@mergington.edu"
        activity = "Drama Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == status.HTTP_200_OK
        
        # Verify enrollment
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email in activities[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert unregister_response.status_code == status.HTTP_200_OK
        
        # Verify removal
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email not in activities[activity]["participants"]
    
    def test_cannot_signup_twice_for_same_activity(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "doublesignup@mergington.edu"
        activity = "Art Studio"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == status.HTTP_200_OK
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_can_signup_for_multiple_activities(self, client):
        """Test that a student can sign up for multiple different activities"""
        email = "multi@mergington.edu"
        activities_list = ["Soccer Team", "Chess Club", "Science Club"]
        
        for activity in activities_list:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == status.HTTP_200_OK
        
        # Verify student is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_list:
            assert email in all_activities[activity]["participants"]
