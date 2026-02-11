import functions_framework
import re

# Email validator
@functions_framework.http
def email_validator(request):
    data = request.get_json(silent=True)
    
    # If format incorrect, provide fail status.
    if not data:
        return {'valid': False, 'error': 'No email provided'}, 400
    
    email = data.get('email', '')
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    valid = bool(re.match(pattern, email))
    
    # Provide go ahead if email format is correct according to regex
    return {'valid': valid, 'email': email}, 200