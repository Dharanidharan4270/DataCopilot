import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents import sql_analyst
from utils.llm_picks import pick_llm
from utils.etl_tool import ETL_TOOL
from models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool
from agents.etl_agent import etl_analyst
from agents.sql_analyst import sql_agent


llm = pick_llm("low")

llm_router = llm.with_structured_output(RouterSchema)


# ---------------------------- DATA AGENT GRAPH ---------------------------- #


def _text(content):
    # Gemini sometimes returns a list of blocks instead of a string
    if isinstance(content, list):
        return "".join(b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content


def router_node(state: DataAgentSchema):
    message = _text(state.message[-1].content)
    route = llm_router.invoke(message).model_dump()["answer"]
    return {"route_response": route}


def etl_node(state: DataAgentSchema):
    message = _text(state.message[-1].content)
    result = etl_analyst.invoke({"message": [HumanMessage(content=message)]})
    final = _text(result["message"][-1].content)
    return {"message": [AIMessage(content=final)]}


def sql_node(state: DataAgentSchema):
    message = _text(state.message[-1].content)
    result = sql_agent.invoke({"user_question": message})
    return {"message": [AIMessage(content=result["final_answer"])]}



data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph.add_conditional_edges("router_node", route_edge,
                                      {
                                          "sql_node": "sql_node",
                                          "etl_node": "etl_node"
                                      })

data_agent = data_agent_graph.compile()

# Optional|




if __name__ == "__main__":

    response = data_agent.invoke(
        {"message":[HumanMessage(content="Give me the number of vehicles manufactured after 2020")],
         "route_response": ""}
    )

    print(response["message"][-1].content)