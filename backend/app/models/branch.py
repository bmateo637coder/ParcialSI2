from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class Branch(Base):
    __tablename__ = "branches"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    address = Column(String(255))
    phone = Column(String(50))
    is_active = Column(Boolean, default=True)
