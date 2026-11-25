from operator import add

from pydantic import BaseModel, Field
from typing import Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

from pydantic import BaseModel, Field
from typing import Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class AgentSchema(BaseModel):
    message: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    user_question: str = ""
    curated_question: str = ""
    prompt_context_query: str = ""
    is_Safe: Literal["Yes", "No"] = "No"
    comments: str = ""
    generated_sql_query: str = ""
    sql_query_execution_result: str = ""
    final_answer: str = ""


class JudgeSchema(BaseModel):
    answer: Literal["Yes", "No"] = Field(..., description="Whether the SQL query is safe to execute")
    comments: str = Field(..., description="Comments on the safety of the SQL query")


class ETLSchema(BaseModel):
    message: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)


class RouterSchema(BaseModel):
    answer: Literal["sql", "etl"] = Field(..., description="Which agent to route the request to")
    comments: str = Field(..., description="Why this route was chosen")


class DataAgentSchema(BaseModel):
    message: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    route_response: str = ""