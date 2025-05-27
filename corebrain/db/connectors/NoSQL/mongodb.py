import time
import json
import re

from typing import Dict, Any, List, Optional, Callable, Tuple
from corebrain.db.connectors.nosql import PYMONGO_IMPORTED

def extract_schema(self, sample_limit: int = 5, collection_limit: Optional[int] = None, 
                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    '''
    extract schema for MongoDB collections
    Args:
        sample_limit (int): Number of samples to extract from each collection.
        collection_limit (Optional[int]): Maximum number of collections to process.
        progress_callback (Optional[Callable]): Function to call for progress updates.
    '''
    schema = {
        "type": self.engine,
        "database": self.db.name,
        "tables": {},  # Depends on DB
    }

    try:
        collections = self.db.list_collection_names()
        if collection_limit is not None and collection_limit > 0:
            collections = collections[:collection_limit]
        total_collections = len(collections)
        for i, collection_name in enumerate(collections):
            if progress_callback:
                progress_callback(i, total_collections, f"Processing collection: {collection_name}")
            collection = self.db[collection_name]

            try:
                doc_count = collection.count_documents({})
                if doc_count <= 0:
                    schema["tables"][collection_name] = {
                        "fields": [],
                        "sample_data": [],
                        "count": 0,
                        "empty": True
                    }
                else:
                    sample_docs = list(collection.find().limit(sample_limit))
                    fields = {}
                    sample_data = []

                    for doc in sample_docs:
                        self._extract_document_fields(doc, fields)
                        processed_doc = self._process_document_for_serialization(doc)
                        sample_data.append(processed_doc)

                    formatted_fields = [{"name": field, "type": type_name} for field, type_name in fields.items()]

                    schema["tables"][collection_name] = {
                        "fields": formatted_fields,
                        "sample_data": sample_data,
                        "count": doc_count,
                    }
            except Exception as e:
                print(f"Error processing collection {collection_name}: {e}")
                schema["tables"][collection_name] = {
                    "fields": [],
                    "error": str(e)
                }
        # Convert the schema to a list of tables
        table_list = []
        for collection_name, collection_info in schema["tables"].items():
            table_data = {"name": collection_name}
            table_data.update(collection_info)
            table_list.append(table_data)
        schema["tables_list"] = table_list
        return schema
    except Exception as e:
        print(f"Error extracting schema: {e}")
        return {
            "type": "mongodb",
            "tables": {},
            "tabbles_list": []
        }

def _extract_document_fields(self, doc: Dict[str, Any], fields: Dict[str, str], 
                            prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> None:
    '''
    Recursively extract fields from a document and determine their types.
    Args:
        doc (Dict[str, Any]): The document to extract fields from.
        fields (Dict[str, str]): Dictionary to store field names and types.
        prefix (str): Prefix for nested fields.
        max_depth (int): Maximum depth for nested fields.
        current_depth (int): Current depth in the recursion.
    '''
    if not PYMONGO_IMPORTED:
        raise ImportError("pymongo is not installed. Please install it to use MongoDB connector.")
    if current_depth >= max_depth:
        return
    for field, value in doc.items():
        if field == "_id":
            field_type = "ObjectId"
        elif isinstance(value, dict):
            if value and current_depth < max_depth - 1:
                self._extract_document_fields(value, fields, f"{prefix}{field}.", max_depth, current_depth + 1)
                continue
            else:
                field_type = f"object"
        elif isinstance(value, list):
            if value and isinstance(value[0], dict) and current_depth < max_depth - 1:
                self._extract_document_fields(value[0], fields, f"{prefix}{field}[].", max_depth, current_depth + 1)
                field_type = f"array<object>"
            elif value:
                field_type = f"array<{type(value[0]).__name__}>"
            else:
                field_type = "array"
        else:
            field_type = type(value).__name__

        field_key = f"{prefix}{field}"
        if field_key not in fields:
            fields[field_key] = field_type

def _process_document_for_serialization(self, doc: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Proccesig a document for serialization of a JSON.
    Args:
        doc (Dict[str, Any]): The document to process.
    Returns:
        Procesed document
    '''
    processed_doc = {}
    for field, value in doc.items():
        if field == "_id":
            processed_doc[field] = str(value)
        elif isinstance(value, list):
            processed_items = []
            for item in value:
                if isinstance(item, dict):
                    processed_items.append(self._process_document_for_serialization(item))
                elif hasattr(item, "__str__"):
                    processed_items.append(str(item))
                else:
                    processed_items.append(item)
            processed_doc[field] = processed_items
        # Convert fetch to ISO
        elif hasattr(value, 'isoformat'):
            processed_doc[field] = value.isoformat()
        # Convert data 
        else:
            processed_doc[field] = value
    return processed_doc

def execute_query(self, query: str) -> List[Dict[str, Any]]:
    '''
    Execute a query on the MongoDB database.
    Args:
        query (str): The query to execute, in JSON format.
    Returns:
        List[Dict[str, Any]]: The results of the query.
    '''

    if not self.client and not self.connect():
        raise ConnectionError("Couldn't establish a connection with NoSQL database.")
    try:
        # Check if the query is a valid JSON string
        filter_dict, projection, collection_name, limit = self._parse_query(query)
        
        # Get the collection
        if not collection_name:
            raise ValueError("Name of the collection not specified in the query")
            
        collection = self.db[collection_name]
        
        # Execute the query
        if projection:
            cursor = collection.find(filter_dict, projection).limit(limit or 100)
        else:
            cursor = collection.find(filter_dict).limit(limit or 100)
        
        # Convert the results to a serializable format
        results = []
        for doc in cursor:
            processed_doc = self._process_document_for_serialization(doc)
            results.append(processed_doc)
        
        return results
    except Exception as e:
    # Reconnect and retry the query
        try:
            self.close()
            if self.connect():
                print("Reconnecting and retrying the query...")
                                
            # Retry the query
            filter_dict, projection, collection_name, limit = self._parse_query(query)
            collection = self.db[collection_name]
                            
            if projection:
                cursor = collection.find(filter_dict, projection).limit(limit or 100)
            else:
                cursor = collection.find(filter_dict).limit(limit or 100)
                            
            results = []
            for doc in cursor:
                processed_doc = self._process_document_for_serialization(doc)
                results.append(processed_doc)                           
                return results
        except Exception as retry_error:
            # If retrying fails, show the original error
            raise Exception(f"Failed to execute the NoSQL query: {str(e)}")
            