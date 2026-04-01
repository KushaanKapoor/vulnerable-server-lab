import sys
sys.path.insert(0, '/home/azureuser/vulnerable_app')
from app import app as application
application.secret_key = 'super-insecure-key-for-lab-only'
