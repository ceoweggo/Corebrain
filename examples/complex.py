from corebrain import init

api_key = "sk_HljTkVLkT2TGMwrpbezpqBmR"
config_id = "59c3e839-fe0a-4675-925d-762064da350b" # MONGODB
#config_id = "8bdba894-34a7-4453-b665-e640d11fd463" # POSTGRES

# Initialize the SDK with API key and configuration ID
corebrain = init(
    api_key=api_key,
    config_id=config_id
)

"""
Corebrain possible arguments (all optionals):

- execute_query (bool)
- explain_results (bool)
- detail_level (string = "full")
"""

result = corebrain.ask("Devuélveme 5 datos interesantes sobre mis usuarios", detail_level="full")

print(result['explanation'])
