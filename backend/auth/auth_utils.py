import os
import logging
from flask import redirect, url_for

# Debug settings
DEBUG = os.environ.get("DEBUG", "false")
DEBUG_LOGGING = DEBUG.lower() == "true"
if DEBUG_LOGGING:
    logging.basicConfig(level=logging.DEBUG)

def get_authenticated_user_details(request_headers):
    user_object = {}

    try:
        ## check the headers for the Principal-Id (the guid of the signed in user)
        if "X-Ms-Client-Principal-Id" not in request_headers.keys():
            ## if it's not, assume we're in development mode and return a default user
            from . import sample_user
            raw_user_object = sample_user.sample_user
        else:
            ## if it is, get the user details from the EasyAuth headers
            raw_user_object = {k:v for k,v in request_headers.items()}

        user_object['user_principal_id'] = raw_user_object['X-Ms-Client-Principal-Id']
        user_object['user_name'] = raw_user_object['X-Ms-Client-Principal-Name']
        user_object['auth_provider'] = raw_user_object['X-Ms-Client-Principal-Idp']
        user_object['auth_token'] = raw_user_object['X-Ms-Token-Aad-Id-Token']
        user_object['client_principal_b64'] = raw_user_object['X-Ms-Client-Principal']
        user_object['aad_id_token'] = raw_user_object["X-Ms-Token-Aad-Id-Token"]

        return user_object
    except Exception as e:
        if DEBUG_LOGGING:
            logging.debug("Error getting user details: {0}".format(e))
        logout()

def logout():
    # Revoke token (if applicable)
    # Example: revoke_token()
    tenant_id = os.environ.get("AUTH_TENANT_ID")

    # Redirect to Azure AD logout endpoint
    return redirect("https://login.microsoftonline.com/{tenant_id}/oauth2/logout?post_logout_redirect_uri={redirect_uri}".format(
        tenant_id=tenant_id,
        redirect_uri=url_for('index', _external=True)
    ))