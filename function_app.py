import azure.functions as func
import re
import json
import datetime
from langchain.agents import create_sql_agent 
from langchain.agents.agent_toolkits import SQLDatabaseToolkit 
from langchain.sql_database import SQLDatabase 
from langchain.llms.openai import OpenAI 
from langchain.agents.agent_types import AgentType
from langchain_experimental.sql import SQLDatabaseChain
from langchain.prompts.prompt import PromptTemplate
import requests
from response_dto import RespondeDto

OPENAI_API_KEY = "test"
connection_string = "mysql+mysqlconnector://test:test@test.mysql.database.azure.com:3306/test"


app = func.FunctionApp()

@app.function_name(name="LLMProcessor")
@app.route(route="question")
@app.http_type("POST")
def chat_function(req: func.HttpRequest) -> func.HttpResponse:
     ct = datetime.datetime.now()
     print("start time:-", ct)
     req_body_bytes = req.get_body()
     req_body = req_body_bytes.decode("utf-8")

     content = json.loads(req_body)

     question = content["question"]

     if question:
        db = SQLDatabase.from_uri(connection_string,
        include_tables=["indexed_properties"],
        sample_rows_in_table_info=1)
        gpt = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY, model_name='gpt-3.5-turbo-16k-0613')
        
        _DEFAULT_TEMPLATE = """Given an input question, first evaluate if the question is related to property search, if not politely answer that your knowladge is only about properties and return the response without quering the database, if yes create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
        Use the following format:

        Question: "Question here"
        SQLQuery: "SQL Query to run"
        SQLResult: "Result of the SQLQuery"
        Answer: "Final answer here"

        Additional rules how to answer:
        Rule 1 - If the input question is related to returning properties then return only the list of listings.
        Rule 2 - If you are returning properties from the Database then the 1st sentence should be always: "Check the results in the side list." 
        Rule 3 - If you are returning properties from the Database return strictly these table fields: id, price, bedrooms, bathrooms, size_sqft, address, city_area, city, state, emirate, country, operation_type, property_type, year, agency_name.
        Rule 2 - Then, strictly based on the result of Sql query generate a straightforward and very short description of maximum of 70 words in total that includes some details about the range number of rooms, range size in square meters and range price in AED currency and other relevant information you find. 
        Please avoid any imaginative or subjective language in the response. Example: "There are three apartments available for sale in Dubai Marina, Dubai. The apartments have 2 to 4 rooms and sizes ranging from 50 to 90 square meters. Prices range from 50,000 to 150,000 AED.". You answer must have maximum of 70 words.
        If the result of the query is 0, then just answer something like: "There are no available properties for you search criteria".
        Rule 3 - If the question is about Studio/Studios then, in case there is a query, the property type is Apartment and number of bedrooms is 0.
        Rule 4 - Never return the url link of the property in your answer
        Only use the following tables:

        {table_info}

        Question: {input}"""
        PROMPT = PromptTemplate(
            input_variables=["input", "table_info", "dialect"], template=_DEFAULT_TEMPLATE
        )

        db_chain = SQLDatabaseChain.from_llm(gpt, db, verbose=True, prompt=PROMPT, use_query_checker=True, return_intermediate_steps=True)
        result = None
        try:
            ct1 = datetime.datetime.now()
            print("start request time:-", ct1)
            result = db_chain(question)
            ct2 = datetime.datetime.now()
            print("end request time:-", ct2)
        except Exception  as e:
            finalReponse = RespondeDto("I am sorry, but my knowladge is only about properties.")
            response_json = json.dumps(finalReponse.__dict__)
            return func.HttpResponse(
             response_json,
             status_code=200
        )

        output = result["intermediate_steps"]
        sql = output[2]
        sqlresult = output[3]
        answer = output[5]

        if sqlresult == "":
            finalReponseError = RespondeDto("There are no available properties for you search criteria")
            response_jsonError = json.dumps(finalReponseError.__dict__)
            return func.HttpResponse(response_jsonError, status_code=200)

        sentences = re.split(r'[.!?]', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            first_sentence = sentences[0]
            if(first_sentence == "Check the results in the side list"):
                id_list = []
                input_string = sqlresult.strip('[]')
                tuples = input_string.split('), (')
                for tup in tuples:
                    id_str, *_ = tup.split(', ')
                    id_str = id_str.strip('(')
                    id_str = id_str.strip(')')
                    id_str = id_str.strip(',')
                    if(id_str != ""):
                        id_list.append(int(id_str))

                data = json.dumps(id_list)

                finalReponse = RespondeDto(answer, None, sql, data)
                response_json = json.dumps(finalReponse.__dict__)
                ct3 = datetime.datetime.now()
                print("end time:-", ct3)
                return func.HttpResponse(response_json, status_code=200)

            else:
                finalReponse = RespondeDto(answer)
                response_json = json.dumps(finalReponse.__dict__)
                return func.HttpResponse(response_json, status_code=200)
        else:
            finalReponse = RespondeDto(answer)
            response_json = json.dumps(finalReponse.__dict__)
            return func.HttpResponse(response_json, status_code=200)

     else:
        return func.HttpResponse(
             "Error processing request",
             status_code=500
        )