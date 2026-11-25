import os
import requests
import pandas as pd
class ETL_TOOL:

    def __init__(self):
        pass

    def extract_load(self, source_url: str, output_folder: str,format:str):
        """
        Extracts data from the source url and loads it into the target file location.

        Args:
            source_url (str): The URL of the source data.
            output_folder (str): The folder where the extracted data will be saved.
            format (str): The format of the extracted data.
        """

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_folder = os.path.join(project_root, output_folder)

        try:
           response= requests.get(source_url)
           response.raise_for_status()  # Raise an error for bad responses
           data = response.json()  # Assuming the data is in JSON format
           file_name=os.path.join(output_folder, f"extracted_data.{format}")

           os.makedirs(output_folder, exist_ok=True) 
           df = pd.DataFrame(data)  # Create the directory if it doesn't exist
           if format=="csv":
                df.to_csv(file_name, index=False)
           elif format=="json":
                df.to_json(file_name, orient='records', lines=True)
           elif format=="parquet":
                df.to_parquet(file_name, index=False)  
           else:
                return f"Unsupported format: {format}. Supported formats are 'csv', 'json', and 'parquet'."
        except requests.exceptions.RequestException as e:
            return f"Error fetching data from {source_url}: {e}"

        return f"Data extracted from {source_url} and saved to {file_name} in {format} format."

    def transform_context(self, file_path: str):
        """
            To gain context about the data, this function reads the first 3 rows of the extracted data file and returns it as a string.

        Args:
            file_path (str): The path to the data file.
        """

        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".json":         
            df = pd.read_json(file_path, lines=True)
        elif file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file format: {file_extension}. Supported formats are 'csv', 'json', and 'parquet'."    


        top3_rows = df.head(3)
        return str(top3_rows)

    def execute_code(self, code: str):
        """
        Executes the provided Python code.

        Args:
            code (str): The Python code to be executed.
        """
        try:
            exec(code)
        except Exception as e:
            return f"Error executing code: {e}" 



if __name__ == "__main__":
    obj=ETL_TOOL()
    print(obj.extract_load("https://archive-api.open-meteo.com/v1/archive?latitude=52.52&longitude=13.41&start_date=2026-11-01&end_date=2026-11-02&hourly=temperature_2m&timezone=Asia%2FBangkok", "data/extracted_data", "csv"))
    print("*************************************")
    print(obj.transform_context("/Users/dharanidharan/Documents/data_agent/data/extracted_data/extracted_data.csv"))
    print("***********************************") 
