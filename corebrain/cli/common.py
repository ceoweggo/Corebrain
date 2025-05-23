"""
Default values for SSO and API connection
"""

DEFAULT_API_URL = "http://localhost:5000"
#DEFAULT_SSO_URL = "http://localhost:3000" # localhost
DEFAULT_SSO_URL = "https://sso.globodain.com" # remote
DEFAULT_PORT = 8765
DEFAULT_TIMEOUT = 10
#SSO_CLIENT_ID = '401dca6e-3f3b-4458-b3ef-f87eaae0398d' # localhost
#SSO_CLIENT_SECRET = 'f9d315ea-5a65-4e3f-be35-b27a933dfb5b' # localhost
SSO_CLIENT_ID = '63d767e9-5a06-4890-a194-8608ae29d426' # remote
SSO_CLIENT_SECRET = '06cf39f6-ca93-466e-955e-cb6ea0a02d4d' # remote
SSO_REDIRECT_URI = 'http://localhost:8765/oauth/callback'
SSO_SERVICE_ID = 2