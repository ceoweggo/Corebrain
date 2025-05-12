"""
Example script to list database schema and configuration details.
This helps diagnose issues with database connections and schema extraction.
"""
import os
import json
import logging
import psycopg2
from corebrain import init

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_postgres_connection(db_config):
    """Verify PostgreSQL connection and list tables directly"""
    logger.info("\n=== Direct PostgreSQL Connection Test ===")
    try:
        # Create connection
        conn = psycopg2.connect(
            host=db_config.get("host", "localhost"),
            user=db_config.get("user", ""),
            password=db_config.get("password", ""),
            dbname=db_config.get("database", ""),
            port=db_config.get("port", 5432)
        )
        
        # Create cursor
        cur = conn.cursor()
        
        # Test connection
        cur.execute("SELECT version();")
        version = cur.fetchone()
        logger.info(f"PostgreSQL Version: {version[0]}")
        
        # List all schemas
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog');
        """)
        schemas = cur.fetchall()
        logger.info("\nAvailable Schemas:")
        for schema in schemas:
            logger.info(f"  - {schema[0]}")
        
        # List all tables in public schema
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = cur.fetchall()
        logger.info("\nTables in public schema:")
        for table in tables:
            logger.info(f"  - {table[0]}")
            
            # Get column info for each table
            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = '{table[0]}';
            """)
            columns = cur.fetchall()
            logger.info("    Columns:")
            for col in columns:
                logger.info(f"      - {col[0]}: {col[1]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in direct PostgreSQL connection: {str(e)}", exc_info=True)

def main():
    # Get API key from environment variable
    api_key = "sk_bH8rnkIHCDF1BlRmgS9s6QAK"
    if not api_key:
        raise ValueError("Please set COREBRAIN_API_KEY environment variable")

    # Get config ID from environment variable
    config_id = "8bdba894-34a7-4453-b665-e640d11fd463"
    if not config_id:
        raise ValueError("Please set COREBRAIN_CONFIG_ID environment variable")

    logger.info("Initializing Corebrain SDK...")
    try:
        corebrain = init(
            api_key=api_key,
            config_id=config_id,
            skip_verification=True  # Skip API key verification due to the error
        )
    except Exception as e:
        logger.error(f"Error initializing SDK: {str(e)}")
        return

    # Print configuration details
    logger.info("\n=== Configuration Details ===")
    logger.info(f"Database Type: {corebrain.db_config.get('type')}")
    logger.info(f"Database Engine: {corebrain.db_config.get('engine')}")
    logger.info(f"Database Name: {corebrain.db_config.get('database')}")
    logger.info(f"Config ID: {corebrain.config_id}")
    
    # Print full database configuration
    logger.info("\n=== Full Database Configuration ===")
    logger.info(json.dumps(corebrain.db_config, indent=2))

    # If PostgreSQL, verify connection directly
    if corebrain.db_config.get("type", "").lower() == "sql" and \
       corebrain.db_config.get("engine", "").lower() == "postgresql":
        verify_postgres_connection(corebrain.db_config)

    # Extract and print schema
    logger.info("\n=== Database Schema ===")
    try:
        schema = corebrain._extract_db_schema(detail_level="full")
        
        # Print schema summary
        logger.info(f"Schema Type: {schema.get('type')}")
        logger.info(f"Total Collections: {schema.get('total_collections', 0)}")
        logger.info(f"Included Collections: {schema.get('included_collections', 0)}")
        
        # Print tables/collections
        if schema.get("tables"):
            logger.info("\n=== Tables/Collections ===")
            for table_name, table_info in schema["tables"].items():
                logger.info(f"\nTable/Collection: {table_name}")
                
                # Print columns/fields
                if "columns" in table_info:
                    logger.info("Columns:")
                    for col in table_info["columns"]:
                        logger.info(f"  - {col['name']}: {col['type']}")
                elif "fields" in table_info:
                    logger.info("Fields:")
                    for field in table_info["fields"]:
                        logger.info(f"  - {field['name']}: {field['type']}")
                
                # Print document count if available
                if "doc_count" in table_info:
                    logger.info(f"Document Count: {table_info['doc_count']}")
                
                # Print sample data if available
                if "sample_data" in table_info and table_info["sample_data"]:
                    logger.info("Sample Data:")
                    for doc in table_info["sample_data"][:2]:  # Show only first 2 documents
                        logger.info(f"  {json.dumps(doc, indent=2)}")
        else:
            logger.warning("No tables/collections found in schema!")

        # Print raw schema for debugging
        logger.info("\n=== Raw Schema ===")
        logger.info(json.dumps(schema, indent=2))
    except Exception as e:
        logger.error(f"Error extracting schema: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True) 