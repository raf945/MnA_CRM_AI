from fastapi.testclient import TestClient
from argon2 import PasswordHasher
from app import app, database
import sqlalchemy
from datetime import date


client = TestClient(app)
ph = PasswordHasher()

# See if login page is served and assert page is html
def test_login_page():
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "").lower()
    assert "username" in response.text.lower()


# Test logging in to website and user is redirected to dashboard
def test_login_post():
    # Create test user
    test_username = "testuser"
    test_password = "testpass"
    hashed_password = ph.hash(test_password)
    
    with database.begin() as conn:
        
        # Delete previous test user
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
        
        # Insert test user into postgres
        conn.execute(
            sqlalchemy.text(
                "INSERT INTO users (username, password_hash, role) VALUES (:username, :password_hash, :role)"
            ),
            {"username": test_username, "password_hash": hashed_password, "role": "rep"}
        )
    
    # Log in
    response = client.post("/login",
        data={"user_name": test_username, "password": test_password},
        follow_redirects=False,
    )
    # Test
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "set-cookie" in response.headers
    
    # Delete user so we can run test again
    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
        
# Test if register page works
def test_register_page():
    response = client.get('/register')
    
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "").lower()
    

# Test if user can be registered
def test_register_user():
    
    # Create test user
    test_username = 'testregisteruser'
    testpass = 'testregisterpass'
    
    with database.begin() as conn:
        # Delete previous test user
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
        
    # Register test user
    response = client.post('/register',
        data={"user_name": test_username, "password": testpass},
        follow_redirects=False,
    )
    
    # Assert reponse is succesful and directs user to dashboard
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "set-cookie" in response.headers
        
    # Check if test user is registered
    with database.begin() as conn:
        result = conn.execute(
            sqlalchemy.text("SELECT id FROM users WHERE username = :username"),
            {"username": test_username}
        ).fetchone()
    
        assert result is not None
    
    # Delete test user
    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
            

# Testing the /dashboard api endpoint, to see if the html is returned
def test_dashboard_page():
    response = client.get('/dashboard')
    
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "").lower()
    

# Test to see if the session cookie is deleted and user is logged out
def test_logout():
    
    # Create test user
    test_username = 'testlogoutuser'
    testpass = 'testlogoutpass'
    
    # Delete previous users
    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
    
    # Register user
    response = client.post('/register',
        data={"user_name": test_username, "password": testpass},
        follow_redirects=False
    )
    # Test if registration and redirection to dashboard worked
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    
    # Assign session_id to cookie then logout
    session_id = response.cookies.get("id")
    assert session_id is not None
    
    # Log out
    logout_response = client.post('/logout')
    assert logout_response.status_code == 200
    assert logout_response.history[0].status_code == 303
    
    # Check if the session id was deleted
    with database.begin() as conn:
        session_deleted = conn.execute(
            sqlalchemy.text("SELECT id FROM sessions WHERE id = :id"),
            {'id': session_id}
        ).fetchone()
        assert session_deleted is None
        
    # Delete test user
    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
        
        
# Test create leads
def test_create_lead():
    
    # Create test user
    test_username = 'testlogoutuser'
    testpass = 'testlogoutpass'
    
    # Delete previous users
    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
    
    # Register user
    response = client.post('/register',
        data={"user_name": test_username, "password": testpass},
        follow_redirects=False
    )
    
    # Test if registration and redirection to dashboard worked
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    
    # Get session id
    session_id = response.cookies.get("id")
    client.cookies.set("id", session_id)
    
    # Example date
    dateToday = date.today().isoformat()
    
    # Test lead
    exampleLead = {
        "im": 'hawk',
        "company_name": 'builders corp',
        "agent_name": 'John',
        'email': 'john@gmail.com',
        'task': 'Contact',
        'date': dateToday
    }
    
    # Post test lead
    response = client.post('/api/leads', json=exampleLead)
    
    # Get test lead from database
    with database.begin() as conn:
        retrieveTestLead = conn.execute(
            sqlalchemy.text("""SELECT im, company_name, agent_name, email, task, action_date FROM leads
                            WHERE im = :im"""),
            {'im': exampleLead['im']}
        ).fetchone()
    
    # Test
    assert retrieveTestLead is not None
    assert retrieveTestLead[0] == exampleLead["im"]
    assert retrieveTestLead[1] == exampleLead["company_name"]
    assert retrieveTestLead[2] == exampleLead["agent_name"]
    assert retrieveTestLead[3] == exampleLead["email"]
    assert retrieveTestLead[4] == exampleLead["task"]
    assert str(retrieveTestLead[5]) == exampleLead["date"]    
        
        
    # Delete from database
    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text("""
                            DELETE FROM leads WHERE im = :im
                            """),
            {'im': exampleLead['im']}
        )
        
    # Test if api succeeded
    assert response.status_code == 200
    assert response.json()["ok"] is True
    
    
# Test if the http get request to get the leads works
def test_get_leads():
     # Create test user
    test_username = 'testuser'
    testpass = 'testpass'
    
    # Delete previous users
    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM users WHERE username = :username"),
            {"username": test_username}
        )
        
    # Register user
    response = client.post('/register',
        data={"user_name": test_username, "password": testpass},
        follow_redirects=False
    )
    
    # Test if registration and redirection to dashboard worked
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    
    # Get session id
    session_id = response.cookies.get("id")
    client.cookies.set("id", session_id)
    
    # Get the user id
    with database.begin() as conn:
        user_id = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :session_id"),
            {'session_id': session_id},
        ).scalar()
        
        # Get username with id
        user_name = conn.execute(
            sqlalchemy.text("SELECT username FROM users WHERE id = :user_id"),
            {'user_id': user_id}
        ).fetchone()
        
        # See if we got the right user
        assert user_name[0] == test_username
        
    # Insert leads
    response = client.get('/api/createleads')
        
    # try to get leads from leads table in sql database
    response = client.get('/api/getleads')
    
    assert response.status_code == 200
    