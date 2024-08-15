import json
from sqlalchemy import text
from database import SessionLocal
from model import get_model
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from typing import List
from langchain.prompts import PromptTemplate

class ServicesTagging(BaseModel):
    provided_services: List[str] = Field(description="List of services that you believe the company provides that exists in the list of posssible services")
    additional_services: List[str] = Field(description="List of services that you believe the company provides that does not exist in the list of posssible services")
    confidence_scores: dict = Field(description="Confidence scores for each identified service (0-100)")

def generate_related_services(preprocessed_text: str):
    llm = get_model().with_structured_output(ServicesTagging)
    parser = PydanticOutputParser(pydantic_object=ServicesTagging)

    format_instructions = parser.get_format_instructions()
    
    session = SessionLocal()
    all_services = session.execute(text("SELECT name,definition FROM subspecialties"))
    # extract all_services = service1, sevice2, service3, ...
    services_dict = {service[0]: service[1] for service in all_services}
    
    template = """
    # You are an expert in identifying services provided by CRO (Contract Research Organization) companies in the life sciences industry.
    # Your task is to analyze the scraped website data from a company's website and identify which services they likely provide.
    # 
    # Context: CROs offer a wide range of services to pharmaceutical, biotechnology, and medical device companies.
    # These services often include clinical trial management, data management, regulatory affairs support, and various laboratory services.


    Scraped website data:
    {preprocessed_text}

    List of possible services and their descriptions:
    {services_list}


    Instructions:
    1. Carefully analyze the scraped website data.
    2. Identify services that the company likely provides, but ONLY from the given list of services in the database. These should be listed under 'provided_services'.
    3. If you identify services that seem to be offered but are NOT in the given list, include them under 'additional_services'.
    4. Assign a confidence score (0-100) to each identified service.
    5. Ignore any non-service related content (e.g., contact information, company history).
    6. If the website content is not related to CRO or scientific services, return "N/A" for all fields.

    {format_instructions}
    Please ensure the response is JSON parsable and remove any HTML tags or markdown formatting.
    
    """

    prompt = PromptTemplate(
        input_variables=["preprocessed_text"],
        partial_variables={"services_list": "\n".join([f"{name}: {desc}" for name, desc in services_dict.items()]), "format_instructions": format_instructions,},
        template=template,
    )
    chain = prompt | llm
    output = chain.invoke({
        "preprocessed_text": preprocessed_text,
    })

    temp1 = output.provided_services
    temp2 = output.additional_services
    temp_provided = []
    temp_additional = []
    # run through temp1, if it exist in all_services, append it to temp_provided, else append it to temp_additional
    # run through temp2, if it exist in all_services, append it to temp_provided, else append it to temp_additional
    for service in temp1:
        if service in services_dict:
            temp_provided.append(service)
        else:
            temp_additional.append(service)
    for service in temp2:
        if service in services_dict:
            temp_provided.append(service)
        else:
            temp_additional.append(service)

    output_dict = {
        "provided_services": temp_provided,
        "additional_services": temp_additional,
        "confidence_scores": output.confidence_scores
    }
    print('output')
    print(output)
    print('Provided Services')
    print(temp_provided)
    print('Additional Services')
    print(temp_additional)
    json_output = json.dumps(output_dict, indent=2)
    
    # Write the JSON string to a file
    with open('output.json', 'w') as f:
        f.write(json_output)

    return output