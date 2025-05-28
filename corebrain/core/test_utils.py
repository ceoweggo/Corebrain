"""
Utilities for testing and validating components.
"""
import json
import random
from typing import Dict, Any, Optional

from corebrain.cli.utils import print_colored
from corebrain.cli.common import DEFAULT_API_URL
from corebrain.network.client import http_session

def generate_test_question_from_schema(schema: Dict[str, Any]) -> str:
    """
    Generates a test question based on the database schema.
    
    Args:
        schema: Database schema
        
    Returns:
        Generated test question
    """
    if not schema or not schema.get("tables"):
        return "What are the available tables?"
    
    tables = schema["tables"]
    
    if not tables:
        return "What are the available tables?"
    
    # Select a random table
    table = random.choice(tables)
    table_name = table["name"]
    
    # Determine the type of question
    question_types = [
        f"How many records are in the {table_name} table?",
        f"Show the first 5 records from {table_name}",
        f"What are the fields in the {table_name} table?",
    ]
    
    # Get columns according to structure (SQL vs NoSQL)
    columns = []
    if "columns" in table and table["columns"]:
        columns = table["columns"]
    elif "fields" in table and table["fields"]:
        columns = table["fields"]
    
    if columns:
        # If we have information from columns/fields
        column_name = columns[0]["name"] if columns else "id"
        
        # Add specific questions with columns
        question_types.extend([
            f"What is the maximum value of {column_name} in {table_name}?",
            f"What are the unique values of {column_name} in {table_name}?",
        ])
    
    return random.choice(question_types)

def test_natural_language_query(api_token: str, db_config: Dict[str, Any], api_url: Optional[str] = None, user_data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Tests a natural language query.
    
    Args:
        api_token: API token
        db_config: Database configuration
        api_url: Optional API URL
        user_data: User data

    Returns:
        True if the test is successful, False otherwise
    """
    try:
        print_colored("\nPerforming natural language query test...", "blue")
        
        # Dynamic import to avoid circular imports
        from db.schema_file import extract_db_schema
        
        # Generate a test question based on the directly extracted schema
        schema = extract_db_schema(db_config)
        print("Retrieved schema: ", schema)
        question = generate_test_question_from_schema(schema)
        print(f"Test question: {question}")
        
        # Prepare the data for the request
        api_url = api_url or DEFAULT_API_URL
        if not api_url.startswith(("http://", "https://")):
            api_url = "https://" + api_url
        
        if api_url.endswith('/'):
            api_url = api_url[:-1]
        
        # Build endpoint for the query
        endpoint = f"{api_url}/api/database/sdk/query"
        
        # Data for the query
        request_data = {
            "question": question,
            "db_schema": schema,
            "config_id": db_config["config_id"]
        }
        
        # Make the request to the API
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        timeout = 15.0  # Reduced maximum waiting time
        
        try:
            print_colored("Sending query to API...", "blue")
            response = http_session.post(
                endpoint,
                headers=headers,
                json=request_data,
                timeout=timeout
            )
            
            # Check the answer
            if response.status_code == 200:
                result = response.json()
                
                # Check if there is an explanation in the result
                if "explanation" in result:
                    print_colored("\nResponse:", "green")
                    print(result["explanation"])
                    
                    print_colored("\n✅ Query test successful!", "green")
                    return True
                else:
                    # If there is no explanation but the API responds, it may be a different format
                    print_colored("\nRespuesta recibida del API (formato diferente al esperado):", "yellow")
                    print(json.dumps(result, indent=2))
                    print_colored("\n⚠️ The API responded, but with a different format than expected.", "yellow")
                    return True
            else:
                print_colored(f"❌ Error in response: Code {response.status_code}", "red")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(response.text[:500])
                return False
                
        except http_session.TimeoutException:
            print_colored("⚠️ Timeout while performing query. The API may be busy or unavailable.", "yellow")
            print_colored("This does not affect the saved configuration.", "yellow")
            return False
        except http_session.RequestError as e:
            print_colored(f"⚠️ Connection error: {str(e)}", "yellow")
            print_colored("Check the API URL and your internet connection.", "yellow")
            return False
            
    except Exception as e:
        print_colored(f"❌ Error performing query: {str(e)}", "red")
        return False