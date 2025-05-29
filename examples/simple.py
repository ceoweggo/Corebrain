from corebrain import init

api_key = "sk_bH8rnkIHCDF1BlRmgS9s6QAK"
#config_id = "c9913a04-a530-4ae3-a877-8e295be87f78" MONGODB
config_id = "8bdba894-34a7-4453-b665-e640d11fd463" # POSTGRES

# Initialize the SDK with API key and configuration ID
corebrain = init(
    api_key=api_key,
    config_id=config_id
)

result = corebrain.ask("Analiza los usuarios y los servicios asociados a estos usuarios.")
print(result["explanation"])

