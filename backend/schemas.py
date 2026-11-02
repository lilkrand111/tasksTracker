from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str
    description: str
    priority: int = 2

class TaskRead(TaskCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    login: str
    password: str = Field(min_length=1)

class UserOut(BaseModel):
    id: int
    login: str
    
    model_config = ConfigDict(from_attributes=True)