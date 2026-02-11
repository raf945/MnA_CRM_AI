from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta, timezone, date
from pydantic import BaseModel
from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from openai import OpenAI
import os
import pymongo
import sqlalchemy
import secrets
import httpx
from google.cloud import secretmanager

app = FastAPI()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sd-coursework")

def googleSecret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

# Store html in templates and mount app
templates = Jinja2Templates(directory='frontend/static')

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

# Secrets
DATABASE_URL = googleSecret("DATABASE_URL")
MONGODB_URL = googleSecret("MONGODB_URL")
#OPENAI_API_KEY = googleSecret("OPENAI_API_KEY")
OPENAI_API_KEY = "123"

# SQL Database connector
database = sqlalchemy.create_engine(DATABASE_URL, pool_pre_ping=True)

# NoSQL
myclient = pymongo.MongoClient(MONGODB_URL)
nosql_database = myclient["mydatabase"]
activity_log = nosql_database["activities_log"]

# Password hasher
ph = PasswordHasher()

# Email validator
EMAIL_VALIDATOR_CLOUD_FUNCTION = "https://europe-west2-sd-coursework.cloudfunctions.net/email-validator"

# Open AI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Redirect to login page
@app.get("/")
async def root():
    return RedirectResponse(url="/login")

# Serve login page
@app.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(request, "login.html")

# Log user function
@app.post('/login')
async def login(request: Request, user_name: str = Form(...), password: str = Form(...)):
    with database.begin() as connector:
        # See if user exists
        result = connector.execute(
            sqlalchemy.text(
                "SELECT id, password_hash FROM users WHERE username = :username"
            ),
            {"username": user_name},
        ).fetchone()
        # If user not found
        if not result:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid username or password"},
                status_code=400,
            )
    
        user_id, password_hash = result

        # Verify password
        try:
            ph.verify(password_hash, password)
        except VerifyMismatchError:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid username or password"},
                status_code=400,
            )
            
        # Create session_id key
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        # Insert session id key along with user_id
        connector.execute(
            sqlalchemy.text(
                "INSERT INTO sessions (id, user_id, expires_at) VALUES (:id, :user_id, :expires_at)"
            ),
            {"id": session_id, "user_id": user_id, "expires_at": expires_at},
        )
        
        # Send activity log to NoSQL DB
        login_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f'User {user_id} logged in'
        }
        
        activity_log.insert_one(login_activity)

        # Set cookie in response
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="id",
            value=session_id,
            httponly=True,
            samesite="lax", 
            secure=False    
        )
                
        return response
    
# Deliver Register page
@app.get('/register', response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse(request, "register.html")

# Register user's details into postgreSQL database
@app.post('/register')
async def registerUser(request: Request, user_name: str = Form(...), password: str = Form(...)):
    with database.begin() as connector:
        # Check if user exists
        result = connector.execute(
            sqlalchemy.text(
                "SELECT id FROM users WHERE username = :username"
            ),
            {"username": user_name},
        ).fetchone()
        
        # if user exists return username already exists
        if result:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"}, status_code=400)
        
        # If user does not exist
        # Hash password
        hashed_password = ph.hash(password)
        
        if not result:
            new_user = connector.execute(
                sqlalchemy.text(
                    "INSERT INTO users (username, password_hash, role) VALUES (:username, :hashed_password, :role) RETURNING id"
                ),
                {'username': user_name, 'hashed_password': hashed_password, 'role': 'rep'},
            ).scalar()
            
        # Create session_id key
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        # Insert session id key along with user_id
        connector.execute(
            sqlalchemy.text(
                "INSERT INTO sessions (id, user_id, expires_at) VALUES (:id, :user_id, :expires_at)"
            ),
            {"id": session_id, "user_id": new_user, "expires_at": expires_at},
        )
        
        # Log activity
        register_activity = {
            'user_id': new_user,
            'timestamp': datetime.now(timezone.utc),
            'time': datetime.now(timezone.utc).strftime('%X'),
            'date': datetime.now(timezone.utc).strftime('%x'),
            'details': f'User {new_user} registered'
        }
        
        activity_log.insert_one(register_activity)
        
        # Set cookie and redirect new user to dashboard
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="id",
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=False
        )
        return response
    

# If user not logged in, then invalidate session
def require_user_id(request: Request) -> int:
    session_id = request.cookies.get("id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")

    with database.begin() as conn:
        row = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {"id": session_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid session")

    return row[0]

        
# Get the dashboard to display
@app.get('/dashboard', response_class=HTMLResponse)
async def home(request: Request):

    # If user tries to type /dashboard without logging in, kick them out
    try:
        require_user_id(request)
    except HTTPException:
        return RedirectResponse(url="/login")  # redirect if not logged in [web:688]
    return templates.TemplateResponse(request, "dashboard.html")
    

# When user logs out, delete session id from database for security and delete cookies from browser
@app.post('/logout',)
async def logout(request: Request):
    session_id = request.cookies.get("id")
    # Authenticate cookie with user_id
    with database.begin() as connector:
        result = connector.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
        {"id": session_id},
        ).fetchone()
        # Delete session_id
        connector.execute(
            sqlalchemy.text("DELETE FROM sessions WHERE id = :id"),
            {"id": session_id},
        )
        # Direct user to login page
        response = RedirectResponse(url="/login", status_code=303)
        
        # Get user_id from result
        user_id = result[0]
        
        # Send activity log to NoSQL DB
        logout_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f'User {user_id} logged out'
        }
        
        activity_log.insert_one(logout_activity)
        
        # Delete cookies
        response.delete_cookie("id")
        
        return response
    
# Create leads from modal menu
@app.post("/api/leads")
async def create_lead(request: Request):
    print("Cookies:", request.cookies)
    data = await request.json()
    
    # Valdiate Email with gloud function
    async with httpx.AsyncClient() as client:
       try:
            validation_email = await client.post( EMAIL_VALIDATOR_CLOUD_FUNCTION, json={"email": data["email"]}, timeout=4.0)
            validation_result = validation_email.json()
            
            if not validation_result.get('valid'):
                return JSONResponse(
                    {"ok": False, "error": "Email format incorrect"},
                    status_code=400
                )
       except Exception as e:
           print(f"Cloud Function error: {e}")
           
    # Get session_id from cookie
    session_id = request.cookies.get("id")
    if not session_id:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

    with database.begin() as connector:
        # Authenticate user
        row = connector.execute(
            sqlalchemy.text("SELECT user_id, expires_at FROM sessions WHERE id = :id"),
            {"id": session_id},
        ).fetchone()

        if not row:
            return JSONResponse({"ok": False, "error": "Invalid session"}, status_code=401)

        user_id, expires_at = row
        
        # if expires_at is in the past delete session
        if expires_at <= datetime.now(timezone.utc):
            connector.execute(
                sqlalchemy.text("DELETE FROM sessions WHERE id = :id"),
                {"id": session_id},
            )
            return JSONResponse({"ok": False, "error": "Session expired"}, status_code=401)

        # Insert lead info from modal menu into sql database
        new_lead_id = connector.execute(
            sqlalchemy.text("""
                INSERT INTO leads (user_id, im, company_name, agent_name, email, task, action_date)
                VALUES (:user_id, :im, :company_name, :agent_name, :email, :task, :action_date)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "im": data["im"],
                "company_name": data["company_name"],
                "agent_name": data["agent_name"],
                "email": data["email"],
                "task": data["task"],
                "action_date": data["date"],
            },
        ).scalar()
        
        # Add to activity log      
        dateReformat = date.fromisoformat(data["date"]).strftime("%x")
        
        create_lead_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f"Lead created by user {user_id} for {data['company_name']} with agent {data['agent_name']} to {data['task']} for {dateReformat}"
        } # Time and date should go on left hand side
        
        activity_log.insert_one(create_lead_activity)
        

    return {"ok": True, "id": new_lead_id}

# Get leads to show on dashboard
@app.get("/api/getleads")
async def get_leads(request: Request):
    session_id = request.cookies.get("id")
    source = request.query_params.get("source")
    
    # Check if logged in
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    
    with database.begin() as connector:
        # Authenticate
        lead_row = connector.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
        {"id": session_id},
        ).fetchone()
        
        if not lead_row:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        user_id = lead_row[0]
        lead_rows=[]
    
        # Check if api request is from leads.js or dashboard.js
        match source:
            case "leadpage":
                lead_rows = connector.execute(
                sqlalchemy.text("""
                                SELECT id, im, company_name, agent_name, email, task, action_date, stage 
                                FROM leads 
                                WHERE user_id = :user_id
                                ORDER BY id DESC
                            """),
                            {"user_id": user_id},
                        ).fetchall()
            case _:
                lead_rows = connector.execute(
                    sqlalchemy.text("""
                                    SELECT id, im, company_name, agent_name, email, task, action_date, stage 
                                    FROM leads 
                                    WHERE user_id = :user_id
                                    AND COALESCE(task_status, 'open') <> 'done'
                                    ORDER BY id DESC
                                """),
                                {"user_id": user_id},
                            ).fetchall()
        
    # Turn leads into JSON
    leads = [
        {
            "id": r[0],
            "im": r[1],
            "company_name": r[2],
            "agent_name": r[3],
            "email": r[4],
            "task": r[5],
            "action_date": r[6],
            "stage": r[7],

        }
        for r in lead_rows
    ]
        
    return {"ok": True, "leads": leads}



# Update task, use pydantic basemodel to type check task is string
class TaskUpdate(BaseModel):
    task: str

@app.patch("/api/leads/{lead_id}/task")
async def updateLeadTask(lead_id: int, payload: TaskUpdate, request: Request):
    session_id = request.cookies.get("id")
    # Check if user logged in
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")

    with database.begin() as conn:
        # Authenticate
        row = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {"id": session_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        user_id = row[0]
        
        # Get task before change
        original_task = conn.execute(
            sqlalchemy.text("""
                SELECT task FROM leads WHERE id = :lead_id AND user_id = :user_id
                            """),
            {"lead_id": lead_id, "user_id": user_id},
        ).fetchone()
        
        # only allow updating your own lead
        updated = conn.execute(
            sqlalchemy.text("""
              UPDATE leads
              SET task = :task
              WHERE id = :lead_id AND user_id = :user_id
            """),
            {"task": payload.task, "lead_id": lead_id, "user_id": user_id},
        ).rowcount
        
        # Get company name and task
        company_info = conn.execute(
            sqlalchemy.text("""
                SELECT company_name, task 
                FROM leads
                WHERE id = :lead_id AND user_id = :user_id
                            """),
            {"lead_id": lead_id, "user_id": user_id}
        ).fetchone()
        
        # Update task and audit for mongodb
        update_lead_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f'User updated lead {company_info[0]} task from {original_task[0]} to {company_info[1]}'
        }
        
        activity_log.insert_one(update_lead_activity)

        if updated == 0:
            raise HTTPException(status_code=404, detail="Lead not found")

    return {"ok": True}


# Update Stage and use pydantic basemodel to ensure stage is string
class StageUpdate(BaseModel):
    stage: str

@app.patch("/api/leads/{lead_id}/stage")
async def updateLeadStage(lead_id: int, payload: StageUpdate, request: Request):
    session_id = request.cookies.get("id")
    
    # Check if logged in
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")

    with database.begin() as conn:
        # Authenticate
        row = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {"id": session_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid session")
        user_id = row[0]
        
        # Get original stage
        original_task = conn.execute(
            sqlalchemy.text("""
                SELECT stage FROM leads WHERE id = :lead_id AND user_id = :user_id
                            """),
            {"lead_id": lead_id, "user_id": user_id},
        ).scalar()

        # Update stage in sql according to lead and user id
        updated = conn.execute(
            sqlalchemy.text("""
              UPDATE leads
              SET stage = :stage
              WHERE id = :lead_id AND user_id = :user_id
            """),
            {"stage": payload.stage, "lead_id": lead_id, "user_id": user_id},
        ).rowcount
        
        # Get lead stage and company name
        company_info = conn.execute(
            sqlalchemy.text("""
                SELECT company_name, stage FROM leads WHERE id = :lead_id AND user_id = :user_id
                            """),
            {"lead_id": lead_id, "user_id": user_id},
        ).fetchone()
        
        
        # Update no sql lead stage
        update_lead_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f'User updated lead {company_info[0]} stage from {original_task} to {company_info[1]}'
        }
        
        activity_log.insert_one(update_lead_activity)

        if updated == 0:
            raise HTTPException(status_code=404, detail="Lead not found")

    return {"ok": True}

# Pydantic class to get metrics and make sure response is ok for simpler success message
class MetricResponse(BaseModel):
    ok: bool
    tasks_status: int
    tasks_due_count:int
    tasks_open: int

# Get leads
@app.get('/api/leads/metrics')
async def getLeadMetrics(request: Request):
    # Check if logged in
    session_id = request.cookies.get("id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    with database.begin() as conn:
        # Authenticate
        auth = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {"id": session_id},
        ).fetchone()
        
        if not auth:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        user_id = auth[0]
        
        # Get tasks that are over due and not lost/won
        tasks_overdue_count = conn.execute(
            sqlalchemy.text("""
                SELECT COUNT(*) FROM leads
                WHERE user_id = :user_id
                AND stage != 'Lost'
                AND stage != 'Won'
                AND action_date <= CURRENT_DATE
                """),
            {"user_id": user_id}
        ).scalar()
        
        # Get tasks that are due today and not lost/won
        tasks_due_count = conn.execute(
            sqlalchemy.text("""
                SELECT COUNT(*) FROM leads
                WHERE user_id = :user_id
                AND stage != 'Lost'
                AND stage != 'Won'
                AND action_date = CURRENT_DATE
                """),
            {'user_id': user_id}
        ).scalar()
        
        # Get tasks that are open not lost/won
        tasks_open = conn.execute(
            sqlalchemy.text("""
                SELECT COUNT(*) FROM leads
                WHERE user_id = :user_id
                AND stage != 'Lost'
                AND stage != 'Won'
            """),
            {'user_id': user_id}
        ).scalar()   
        
    return MetricResponse(ok=True, tasks_status=tasks_overdue_count, tasks_due_count=tasks_due_count, tasks_open=tasks_open)


# Complete leads and remove from today's task
@app.post('/api/leads/{leadId}/complete')
def completeLead(leadId: int, request: Request):
    session_id = request.cookies.get("id")
    # Check if logged in
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    with database.begin() as conn:
         # Authenticate
        auth = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {"id": session_id},
        ).fetchone()
        
        if not auth:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        user_id = auth[0]
        
        # Get current datetime
        current_datetime = datetime.now()

        # Get datetime 7 days in advance
        future_datetime = current_datetime + timedelta(days=7)
        
        # Set datetime to be 7 days in advance
        conn.execute(
            sqlalchemy.text("""
                            UPDATE leads 
                            SET task_status = 'done',
                            action_date = :new_date
                            WHERE id = :lead_id
                            AND user_id = :user_id
                            RETURNING id
                            """),
            {"user_id": user_id, "lead_id": leadId, "new_date": future_datetime},
        ).fetchone()
        
        # Get company info to update mongodb
        company_info = conn.execute(
            sqlalchemy.text("""
                SELECT company_name FROM leads WHERE id = :lead_id AND user_id = :user_id
                            """),
            {"user_id": user_id, "lead_id": leadId},
        ).scalar()
        
        
        # Update no sql lead status
        update_lead_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f'User completed lead {company_info}'
        }
        
        activity_log.insert_one(update_lead_activity)

    return {"ok": True, "lead_id": leadId}


# Get date from user and update action date of lead
@app.patch('/api/leads/{leadId}/reschedule')
async def rescheduleLead(leadId:int, request: Request):
    # Await for user to set new action date
    newDateTime = await request.json()

    convertedDateTime = datetime.strptime(newDateTime['action_date'], '%Y-%m-%d')
    datetime_now = datetime.now()

    session_id = request.cookies.get('id')
    
    # Check if logged in
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    with database.begin() as conn:
        # Authenticate request
        auth = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {'id': session_id},
        ).fetchone()
        
        if not auth:
            raise HTTPException(status_code=401, details="Invalid session")
        
        user_id = auth[0]
        
        # Get previous date time and company name
        company_info = conn.execute(
            sqlalchemy.text("""
                SELECT company_name, action_date FROM leads WHERE id = :lead_id AND user_id = :user_id
                            """),
            {"user_id": user_id, "lead_id":leadId},
        ).fetchone()

        # If lead's datetime is set to before today's date, then remove task completion status i.e. 'done' so that we can display the lead on the main page
        if datetime_now >= convertedDateTime:
            # Update SQL database with new action date
            conn.execute(
                sqlalchemy.text("""
                    UPDATE leads
                    set action_date = :newDateTime,
                    task_status = NULL
                    WHERE id = :lead_id
                    AND user_id = :user_id
                                """),
                {"user_id": user_id, "lead_id":leadId, "newDateTime": newDateTime['action_date']}
        ) 
        else:
            # Update SQL database with new action date
            conn.execute(
                sqlalchemy.text("""
                    UPDATE leads
                    set action_date = :newDateTime
                    WHERE id = :lead_id
                    AND user_id = :user_id
                                """),
                {"user_id": user_id, "lead_id":leadId, "newDateTime": newDateTime['action_date']}
            )
            
        # Update no sql schedule status
        update_lead_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f'User rescheduled lead: {company_info[0]} from {company_info[1]} to {newDateTime["action_date"]}'
        }
        
        activity_log.insert_one(update_lead_activity)
        
        return {"ok": True, "lead_id": leadId}
    

# Get activity log to show in activity tab
@app.get('/api/activity')
async def getActivityLog(request: Request):
    session_id = request.cookies.get('id')
    # Check if logged in
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    with database.begin() as conn:
        # Authenticate request
        auth = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {'id': session_id},
        ).fetchone()
        
        if not auth:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        user_id = auth[0]
        
        # Get activities associated with user id and put into list to return to frontend
        activity_query = { 'user_id': user_id }
        current_activity_log = list(activity_log.find(activity_query, {"_id": 0}))
        
        
        return {'ok': True, 'activity_log': current_activity_log}
    
# Chatbot that calls OpenAI API 
class PromptPayload(BaseModel):
    prompt: str

@app.post('/api/llm')
async def sendPrompt(payload: PromptPayload, request: Request):
    
    # Authentication
    session_id = request.cookies.get('id')
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    with database.begin() as conn:
        # Authenticate request
        auth = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {'id': session_id},
        ).fetchone()
        
        if not auth:
            raise HTTPException(status_code=401, detail="Invalid session")
    
    # Get response from GPT, reference: https://github.com/openai/openai-python
    gpt_response = client.responses.create(
        model="gpt-5-nano",
        input = payload.prompt
    )
    
    # Extract text
    text = ""
    try:
        text = gpt_response.output_text
    except Exception:
        text = str(gpt_response)

    return { 'ok': True, 'response': text}


# Delete lead from sql database
@app.delete('/api/leads/{leadId}/delete')
async def deleteLead(leadId: int, request: Request):

    # Get session id
    session_id = request.cookies.get('id')

    # Check if logged in
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    with database.begin() as conn:
        # Authenticate request
        auth = conn.execute(
            sqlalchemy.text("SELECT user_id FROM sessions WHERE id = :id"),
            {'id': session_id},
        ).fetchone()

        # Define user id
        user_id = auth[0]

        # Get previous date time and company name
        company_info = conn.execute(
            sqlalchemy.text("""
                SELECT company_name FROM leads WHERE id = :lead_id AND user_id = :user_id
                            """),
            {"user_id": user_id, "lead_id":leadId},
        ).fetchone()

        # If the user id is not the same as session id then throw error
        if not auth:
            raise HTTPException(status_code=401, detail="Invalid session")

        conn.execute(
            sqlalchemy.text("DELETE FROM leads WHERE id = :lead_id AND user_id = :user_id"),
            {"lead_id": leadId, "user_id": user_id}
        )

        # Update no sql schedule status
        update_lead_activity = {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc),
            'time': (datetime.now(timezone.utc).strftime('%X')),
            'date': (datetime.now(timezone.utc).strftime('%x')),
            'details': f'User deleted lead: {company_info[0]}'
        }
        
        activity_log.insert_one(update_lead_activity)

    return { 'ok': True}
    
