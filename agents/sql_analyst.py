import os
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.llm_picks import pick_llm
from models.schema import AgentSchema, JudgeSchema

from langchain_core.messages import HumanMessage, AIMessage

from utils.database import DatabaseUtil

from langgraph.graph import StateGraph, START,  END



def curate_question(state: AgentSchema) -> AgentSchema:
   
    user_question = state.user_question
    llm = pick_llm("low")
    response = llm.invoke(f"""You are a Business Intelligence Analyst.

Rewrite the user's question to make it clear and precise for SQL generation.

Rules:
- Preserve the original intent.
- Correct grammar and remove ambiguity.
- Do not invent dates, filters, metrics, or assumptions.
- Do not answer the question or generate SQL.
- Return only ONE refined question.
- If the question is already clear, keep it unchanged.

User Question: {user_question}""")

    
    content=response.content
    if isinstance(content, list):
        content = "\n".join(
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )


    state.curated_question = content
    state.message=state.message+[HumanMessage(content=content)]
    return state

def add_context_to_prompt(state: AgentSchema) -> AgentSchema:
   
    curated_question=state.curated_question


    db_obj=DatabaseUtil({
     "host": os.getenv("host"),
    "port": os.getenv("port"),
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "database": os.getenv("database")
    })

    schema_info=db_obj.schema_details(os.getenv("database"))

    prompt=f""" You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Mysql SQL query that can be executed on the database. You are provided 
    with the user's original query and the details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.  

    User Question: {curated_question}

    DataBase Details : {schema_info}
    
    """
    state.prompt_context_query=prompt

    return state

def generate_sql(state : AgentSchema)->AgentSchema:

    llm=pick_llm("low")
    prompt=state.prompt_context_query
    response=llm.invoke(prompt)
    content=response.content
    if isinstance(content, list):
            content = "\n".join(
                block["text"]
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )

    state.generated_sql_query=content


    return state

def isSafe(state: AgentSchema) -> AgentSchema:

    generated_sql_query=state.generated_sql_query

    llm=pick_llm("low")

    llm_judge=llm.with_structured_output(JudgeSchema)





    prompt=f"""You are a Sql judge. Your task is to determine whether the SQL query is safe to execute on the database or not.
           the query must be used to data retrival only. It should not be used to modify the database in any way.
           if the query is safe to execute, respond with 'Yes' and provide a brief comment on why it is safe.
           if the query is not safe to execute, respond with 'No' and provide a brief
           You are provided with SQL query 

           SQL Query: {generated_sql_query}
          """

    response=llm_judge.invoke(prompt).model_dump()
    print(f"Judge Response: {response}")

    is_Safe=response["answer"]
    comments=response["comments"]

    state.is_Safe=is_Safe
    state.comments=comments

    return state

def cancelled(state : AgentSchema)->AgentSchema:
    comments=state.comments
    state.final_answer=f"The query is unsafe to execute and the reason is {comments}"
    state.message=state.message+[AIMessage(content=state.final_answer)] 
    return state
    

def execute_query(state: AgentSchema)->AgentSchema:

    run_obj=DatabaseUtil({ "host": os.getenv("host"),
        "port": os.getenv("port"),
        "user": os.getenv("user"),
        "password": os.getenv("password"),
        "database": os.getenv("database")
        })


    result=run_obj.execute_sql(state.generated_sql_query)

    state.sql_query_execution_result=result


    return state

def final_answer(state : AgentSchema)->AgentSchema:

    prompt=f"""You are an SQL analyst agent. Your task is to provide a final answer to the user based on the result of executing the SQL query on the database and the user's original question.
    You are provided with the user's original question and the result of executing the SQL query on the database. Your answer should be concise and directly address the user's question based on the data retrieved from the database. If the result is empty or does not provide a clear answer to the user's question, you should indicate that the answer could not be determined from the available data. Avoid providing any additional information or context that is not directly relevant to the user's question. Your response should be clear, concise, and
    directly address the user's question based on the data retrieved from the database.

    User Question: {state.user_question}

    SQL Query: {state.generated_sql_query}

    SQL Query Execution Result: {state.sql_query_execution_result}

    """

    llm=pick_llm("low")

    result=llm.invoke(prompt)
    content=result.content
    if isinstance(content, list):
                content = "\n".join(
                    block["text"]
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )

    state.final_answer=content

    state.message=state.message+[AIMessage(content=content)]
    return state

sql_analyst_graph=StateGraph(AgentSchema)

sql_analyst_graph.add_node(curate_question,name="curate_question")
sql_analyst_graph.add_node(add_context_to_prompt,name="add_context_to_prompt")
sql_analyst_graph.add_node(generate_sql,name="generate_sql")
sql_analyst_graph.add_node(isSafe,name="isSafe")
sql_analyst_graph.add_node(cancelled,name="cancelled")
sql_analyst_graph.add_node(execute_query,name="execute_query")
sql_analyst_graph.add_node(final_answer,name="final_answer")

sql_analyst_graph.add_edge(START,"curate_question")
sql_analyst_graph.add_edge("curate_question","add_context_to_prompt"   )
sql_analyst_graph.add_edge("add_context_to_prompt","generate_sql")
sql_analyst_graph.add_edge("generate_sql","isSafe")

def is_safe_condition(state: AgentSchema) -> str:
    if state.is_Safe == "Yes":
        return "execute_query"
    else:
        return "cancelled"

sql_analyst_graph.add_conditional_edges("isSafe", is_safe_condition,
    {
        "execute_query": "execute_query",
        "cancelled": "cancelled"
    }
)

sql_analyst_graph.add_edge("cancelled",END)
sql_analyst_graph.add_edge("execute_query","final_answer") 
sql_analyst_graph.add_edge("final_answer",END)

sql_agent=sql_analyst_graph.compile()







 
    
    











    