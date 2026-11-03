from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str
    description: str
    priority: int = 2

class TaskRead(TaskCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

class UserOut(BaseModel):
    id: int
    login: str
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str