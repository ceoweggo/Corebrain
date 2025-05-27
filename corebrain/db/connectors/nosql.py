'''
NoSQL Database Connector
This module provides a basic structure for connecting to a NoSQL database.
It includes methods for connecting, disconnecting, and executing queries.
'''

import time
import json
import re

from typing import Dict, Any, List, Optional, Callable, Tuple

# Try'ies for imports DB's (for now only mongoDB)
try: 
    import pymongo
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_IMPORTED = True
except ImportError:
    PYMONGO_IMPORTED = False
    # Whe nadding new DB type write a try to it from user

try:
    import corebrain.db.connectors.NoSQL.mongodb as mongodb_subconnector
    MONGO_MODULES = True
except ImportError:
    MONGO_MODULES = False


from corebrain.db.connector import DatabaseConnector
class NoSQLConnector(DatabaseConnector):
    '''
    NoSQL Database Connector
    This class provides a basic structure for connecting to a NoSQL database.
    It includes methods for connecting, disconnecting, and executing queries.
    '''
    def __init__(self, config: Dict[str, Any]):
      '''
      Initialize the NoSQL database connector.
      Args:
          engine (str): Name of the database.
          config (dict): Configuration dictionary containing connection parameters.
      '''
      super().__init__(config)

      self.conn = None
      self.engine = config.get("engine", "").lower()
      self.config = config
      self.connection_timeout = 30 # seconds
      '''
      self.engine = config.get("engine", "").lower()
      self.client = None
      self.db = None
      self.config = config
      self.connection_timeout = 30 # seconds
      '''
      match self.engine:
        case "mongodb":
            if not PYMONGO_IMPORTED:
                raise ImportError("pymongo is not installed. Please install it to use MongoDB connector.")
        case _:
            pass
      

    def connect(self) -> bool:
        '''
          Connection with NoSQL DB's
          Args:
            self.engine (str): Name of the database.
        '''
        try:

            start_time = time.time()

            while time.time() - start_time < self.connection_timeout:
                try:
                    if self.engine == "mongodb":
                        # Checking if pymongo is imported
                        if not PYMONGO_IMPORTED:
                            raise ImportError("pymongo is not installed. Please install it to use MongoDB connector.")
                        
                        # Construction of the MongoDB connection
                        if "connection_string" in self.config:

                            # Check if connection string is provided
                            connection_string = self.config["connection_string"]

                            if "connectTimeoutMS=" not in connection_string:
                                if "?" in connection_string:
                                    connection_string += "&connectTimeoutMS=10000"
                                else:
                                    connection_string += "?connectTimeoutMS=10000"
                            # Connecting to MongoDB using the connection string
                            self.client = pymongo.MongoClient(connection_string)

                        else:
                            # Setup for MongoDB connection parameters
                            mongo_params = {
                                "host": self.config.get("host", "localhost"),
                                "port": int(self.config.get("port", 27017)),
                                # 10000 = 10 seconds
                                "connectTimeoutMS": 10000,
                                "serverSelectionTimeoutMS": 10000,
                            }

                            # Required parameters
                            if self.config.get("user"):
                                mongo_params["username"] = self.config["user"]
                            if self.config.get("password"):
                                mongo_params["password"] = self.config["password"]

                            # Optional parameters
                            if self.config.get("authSource"):
                                mongo_params["authSource"] = self.config["authSource"]
                            if self.config.get("authMechanism"):
                                mongo_params["authMechanism"] = self.config["authMechanism"]

                            # Insert parameters for MongoDB
                            self.client = pymongo.MongoClient(**mongo_params)
                    #
                    # If adding new db add thru self.engine variable
                    #
                    else:
                        raise ValueError(f"Unsupported NoSQL database: {self.engine}")             
                    if self.conn:
                        if self.engine == "mongodb":
                            # Testing connection for MongoDB
                            self.client.admin.command('ping')

                            # If connection is successful, set the database
                            db_name = self.config.get("database", "")
                            if not db_name:
                                # If database name is not specified, use the first available database
                                db_names = self.client.list_database_names()
                                if not db_names:
                                    raise ValueError("No database names found in the MongoDB server.")
                                # Exclude system database (MongoDB) from the list
                                system_dbs = ["admin", "local", "config"]
                                for name in db_names:
                                    if name not in system_dbs:
                                        db_name = name
                                        break
                                if not db_name:
                                    db_name = db_names[0]
                                print(f"Not specified database name. Using the first available database: {db_name}")
                            # Connect to the specified database
                            self.db = self.client[db_name]
                            return True
                        else:
                            # If the engine is not Supported, raise an error
                            raise ValueError(f"Unsupported NoSQL database: {self.engine}")
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    # If connection fails, check if timeout is reached
                    if time.time() - start_time > self.connection_timeout:
                        print(f"Connection to {self.engine} timed out after {self.connection_timeout} seconds.")
                        time.sleep(2)
                        self.close()
                        return False
        except Exception as e:
            # If cannot connect to the database, print the error
            print(f"Error connecting to {self.engine}: {e}")
            return False

    def extract_schema(self, sample_limit: int = 5, collection_limit: Optional[int] = None, 
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        '''
        Extract schema from the NoSQL database.
        Args:
            sample_limit (int): Number of samples to extract for schema inference.
            collection_limit (int): Maximum number of collections to process.
            progress_callback (Callable): Optional callback function for progress updates.
        Returns:
            Dict[str, Any]: Extracted schema information.
        '''
        if not self.client and not self.connect():
            return {
                "type": self.engine,
                "tables": {},
                "tables_list": []
            }
        match self.engine:
            case "mongodb":

                if not PYMONGO_IMPORTED:
                    raise ImportError("pymongo is not installed. Please install it to use MongoDB connector.")
                if not MONGO_MODULES:
                    raise ImportError("MongoDB subconnector modules are not available. Please check your installation.")
                # Use the MongoDB subconnector to extract schema
                return mongodb_subconnector.extract_schema(self, sample_limit, collection_limit, progress_callback)
            # If adding new db add thru self.engine variable          
            # Add case when is needed new DB type
            case _:
                return {
                    "type": self.engine,
                    "database": self.db.name,
                    "tables": {},  # Depends on DB
                }
                    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Runs a NoSQL (or other) query with improved error handling
        
        Args:
            query: A NoSQL (or other) query in JSON format or query language
            
        Returns:
            List of resulting documents.
        """
        if not self.conn and not self.connect():
            raise ConnectionError("Couldn't establish a connection with NoSQL database.")
        
        try:
            if self.engine == "mongodb":
                if not PYMONGO_IMPORTED:
                    raise ImportError("pymongo is not installed. Please install it to use MongoDB connector.")
                if not MONGO_MODULES:
                    raise ImportError("MongoDB subconnector modules are not available. Please check your installation.")
                # Use the MongoDB subconnector to execute the query
                return mongodb_subconnector.execute_query(self, query)
        except Exception as e:
            try:
                # Attempt to reconnect and retry the query
                self.close()
                if self.connect():
                    print("Reconnecting and retrying the query...")
                    return mongodb_subconnector.execute_query(self, query)
            except Exception as retry_error:
                # If retrying fails, show the original error
                raise Exception(f"Failed to execute the NoSQL query: {str(e)}")
    def close(self) -> None:
        """
        Close the connection to the NoSQL database.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            print(f"Connection to {self.engine} closed.")
        else:
            print(f"No active connection to {self.engine} to close.")
    def __del__(self):
        """
        Destructor to ensure the connection is closed when the object is deleted.
        """
        self.close()