from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
load_dotenv()

def pick_llm(level : str):
    """
    Picks the appropriate LLM based on the level of complexity of the SQL query.

    Args:
        level (str): The level of complexity of the SQL query. Can be "simple", "medium", or "complex".

    Returns:
        str: The name of the LLM to be used for generating SQL queries.
    """
    if level == "low":
        llm=ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0)
    elif level == "medium":
        llm=ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)
    elif level == "high":
        llm=ChatGoogleGenerativeAI(model="gemini-3.5", temperature=0)

    return llm




