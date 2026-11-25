import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.schema import ETLSchema
from utils.etl_tool import ETL_TOOL
from utils.llm_picks import pick_llm
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import AIMessage,HumanMessage,ToolMessage
from langchain.tools import tool
from langgraph.graph import StateGraph, START,END
import re




#---------------tools-----------------
@tool
def extract_load_tool(source_url: str, output_folder: str, format: str) -> str:
    """
    Extracts data from the source URL and loads it into the target file location.

    Args:
        source_url (str): The URL of the source data.
        output_folder (str): The folder where the extracted data will be saved.
        format (str): The format of the extracted data.

    Returns:
        str: A message indicating the success or failure of the operation.
    """
    etl_tool = ETL_TOOL()
    return etl_tool.extract_load(source_url, output_folder, format)

@tool
def transform_context_tool(file_path: str,output_folder: str, user_question: str) -> str:
    """
    Have the 3 rows of the data file.It then generates the Pandas code to transform and save the data based on the user's question.

    Args:
        file_path (str): The path to the data file.
        output_folder (str): The folder where the transformed data will be saved.
        user_question (str): The question asked by the user.

    Returns:
        str: A message indicating the success or failure of the operation.
"""

    etl_tool=ETL_TOOL()
    top_3_rows=etl_tool.transform_context(file_path)

    llm=pick_llm("low")

    prompt=f"""You are a Python Data Analyst who uses Pandas to analyze data. 
            You need to provide only the Pandas Code that will help to perform the right ETL operations on the data stored in the file : {file_path}
            as per the user's question. Do not provide any explanation or comments, only
            the code should be provided. The code should be in a format that can be executed 
            in a Python environment with Pandas installed. 
            Don't write anything else than Pandas Code. \n
            
            Create the Pandas Dataframe from the data stored in the file : {file_path} and then 
            write the code to transform and save the data at {output_folder}.
            Here's the user's question: {user_question}\n
            Here's the context of the data you will be analyzing: {top_3_rows}"""

    response=llm.invoke(prompt)

    content=response.content
    if isinstance(content, list):
            content = "\n".join(
                block["text"]
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
    content = re.sub(r"^```(?:python)?\s*|\s*```$", "", content.strip())

#----execute code-----
    results=etl_tool.execute_code(content)

    return f"The code is Executed. Results: {results}"


    
tools = [extract_load_tool, transform_context_tool]


def llm_node(state: ETLSchema) -> ETLSchema:
    message = state.message
    prompt = f"""
            You are a Python Data Analyst who has access to tools that can extract and load, 
            transform and load data. You will be provided with a user's question 
            and you would need to perform the right ETL operations as per the user's question. 
            If the operation is performed then inform the user and end the coversation.
            Here's the chat history: {message}\n
    """

    
    llm = pick_llm("low") 
    llm_bind=llm.bind_tools(tools)

    response = llm_bind.invoke(prompt)
    
    state.message=state.message+[response]
    return state

def tool_node(state: ETLSchema)-> ETLSchema:
    tool_by_name={
          tool.name: tool 
          for tool in tools}
    tool_results=[]
    tool_calls=state.message[-1].tool_calls

 
    for tool_call in tool_calls:
        tool=tool_by_name[tool_call['name']]
        observation=tool.invoke(tool_call['args'])

        tool_results.append(ToolMessage(content=observation,tool_call_id=tool_call['id'],name=tool_call['name']))

    state.message=state.message+tool_results
    return state


etl_analyst_graph=StateGraph(ETLSchema)
etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tool_node", tool_node) 

etl_analyst_graph.add_edge(START, "llm_node")

def is_tool_call(state:ETLSchema):
    tool_calls = state.message[-1].tool_calls

    if tool_calls:
        return "tool_node"
    else:
        return "end"

etl_analyst_graph.add_conditional_edges(
    "llm_node",is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END
    }
)

etl_analyst_graph.add_edge("tool_node", "llm_node")

etl_analyst=etl_analyst_graph.compile()
         

if __name__ == "__main__":
    with open("etl_analyst_graph.png", "wb") as f:
        f.write(etl_analyst.get_graph().draw_mermaid_png())
   
    # print(etl_analyst.invoke({"message": [HumanMessage(content="Extract data from the source URL 'https://archive-api.open-meteo.com/v1/archive?latitude=52.52&longitude=13.41&start_date=2026-11-01&end_date=2026-11-02&hourly=temperature_2m&timezone=Asia%2FBangkok' and load it into the folder 'data/extracted_data' in csv format")]}))
    # print(etl_analyst.invoke("Extract data from the source URL 'https://archive-api.open-meteo.com/v1/archive?latitude=52.52&longitude=13.41&start_date=2026-11-01&end_date=2026-11-02&hourly=temperature_2m&timezone=Asia%2FBangkok' and load it into the folder 'data/extracted_data' in CSV format"))
    print(etl_analyst.invoke({"message": [HumanMessage(content="I want to transform the data stored in the file 'data/extracted_data/extracted_data.csv' and save it into the folder 'data/transformed_data' based on the user's question: 'What is the average temperature for each hour?' in csv format")]}))