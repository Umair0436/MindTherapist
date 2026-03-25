from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# SQLite file will be created at this path — mindtherapist.db in the project folder
DATABASE_URL = "sqlite:///./mindtherapist.db"

# Engine = actual connection to the database
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite with FastAPI
)

Base = declarative_base()

# SessionLocal = a new database session will be created for each request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---- TABLE 1: Sessions ----
# Named TherapySession to avoid conflict with SQLAlchemy's own Session class
class TherapySession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)          
    age = Column(Integer)                           
    symptoms = Column(Text)                          
    behavior = Column(Text)                          
    tone = Column(Text)                              
    is_active = Column(Boolean, default=True)        
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship — easily access all messages and reports linked to this session
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="session", cascade="all, delete-orphan")


# ---- TABLE 2: Messages ----
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)  
    role = Column(String)                            
    message = Column(Text)                           
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("TherapySession", back_populates="messages")


# ---- TABLE 3: Reports ----
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    scores_json = Column(Text)                       
    summary = Column(Text)
    strengths = Column(Text)                         
    improvements = Column(Text)                      
    next_steps = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TherapySession", back_populates="reports")


# ---- Helper: Dependency Injection ----
# Used to inject a fresh database session into each FastAPI endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  


# ---- Create Tables ----
# Runs on app startup — creates all tables if they don't already exist
def init_db():
    Base.metadata.create_all(bind=engine)