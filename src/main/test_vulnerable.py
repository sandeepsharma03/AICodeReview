#!/usr/bin/env python
"""
Test file with intentional security, performance, code quality,
best practice, and maintainability issues.
"""

import sqlite3
import pickle
import os
import subprocess
from PIL import Image

# SECURITY ISSUE: Hardcoded credentials
DB_PASSWORD = "admin123"
API_KEY = "sk-1234567890abcdef"

class UserDataProcessor:
    """
    Process user data without proper validation.
    MAINTAINABILITY ISSUE: Long class with too many responsibilities
    """
    
    def __init__(self):
        # SECURITY ISSUE: No input validation
        self.db_path = os.environ.get('DB_PATH', '/tmp/users.db')
        self.users = []
    
    def query_user(self, user_id):
        """
        SECURITY ISSUE: SQL Injection vulnerability
        PERFORMANCE ISSUE: No connection pooling
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # SQL Injection vulnerability - user_id not parameterized
        query = f"SELECT * FROM users WHERE id = {user_id}"
        cursor.execute(query)
        result = cursor.fetchone()
        
        conn.close()
        return result
    
    def process_batch_data(self, data_list):
        """
        PERFORMANCE ISSUE: Inefficient nested loops (O(n²) complexity)
        CODE QUALITY ISSUE: No error handling
        MAINTAINABILITY ISSUE: Magic numbers without explanation
        """
        results = []
        for i in range(len(data_list)):
            for j in range(len(data_list)):
                if data_list[i]['id'] == data_list[j]['id'] and i != j:
                    # Duplicate found - process it
                    results.append(data_list[i])
        
        # PERFORMANCE ISSUE: Loading entire file into memory
        with open('large_file.bin', 'rb') as f:
            content = f.read()
        
        # BEST PRACTICES ISSUE: Using pickle without verification
        unpickled = pickle.loads(content)
        return results + [unpickled]
    
    def execute_user_command(self, command):
        """
        SECURITY ISSUE: Command injection vulnerability
        BEST PRACTICES ISSUE: shell=True is dangerous
        """
        result = subprocess.run(command, shell=True, capture_output=True)
        return result.stdout.decode()
    
    def process_image(self, image_data):
        """
        SECURITY ISSUE: No validation of image data
        CODE QUALITY ISSUE: Missing exception handling
        MAINTAINABILITY ISSUE: Unclear variable names
        """
        img = Image.open(image_data)
        w = img.width
        h = img.height
        
        # Transform without validation
        new_img = img.resize((w * 2, h * 2))
        
        # PERFORMANCE ISSUE: Creating many objects in loop
        thumbnails = []
        for x in range(1000):
            tn = img.thumbnail((100, 100))
            thumbnails.append(tn)
        
        return new_img
    
    def validate_email(self, email):
        """
        CODE QUALITY ISSUE: No proper validation
        BEST PRACTICES ISSUE: Missing type hints
        """
        if '@' in email:  # Inadequate validation
            return True
        return False
    
    def fetch_and_cache_data(self, url):
        """
        SECURITY ISSUE: No SSL verification
        PERFORMANCE ISSUE: No caching mechanism implemented
        BEST PRACTICES ISSUE: Not using connection timeout
        """
        import requests
        
        response = requests.get(url, verify=False, timeout=None)
        
        # Cache implementation missing
        return response.json()
    
    def process_user_input(self, raw_input):
        """
        CODE QUALITY ISSUE: No input sanitization
        MAINTAINABILITY ISSUE: Overly complex logic
        """
        if raw_input:
            data = eval(raw_input)  # SECURITY: eval is dangerous
        else:
            data = None
        
        # Overly nested and unclear logic
        if data:
            if isinstance(data, dict):
                if 'user' in data:
                    if 'name' in data['user']:
                        if len(data['user']['name']) > 0:
                            return data['user']['name']
        
        return "Unknown"
    
    def get_user_by_id(self, user_id):
        """
        MAINTAINABILITY ISSUE: No docstring for parameters
        BEST PRACTICES ISSUE: No type hints
        PERFORMANCE ISSUE: Full table scan for every query
        """
        for user in self.users:
            if user['id'] == user_id:
                return user
        return None


def load_config_from_file(config_path):
    """
    SECURITY ISSUE: No path validation - potential directory traversal
    BEST PRACTICES ISSUE: Missing error handling
    """
    with open(config_path, 'r') as f:
        return pickle.load(f)


def authenticate_user(username, password):
    """
    SECURITY ISSUE: No rate limiting, plaintext comparison
    CODE QUALITY ISSUE: Hardcoded credentials
    """
    # Hardcoded user database - should never do this
    users = {'admin': 'password123', 'user': 'user456'}
    
    if username in users and users[username] == password:
        return True
    return False


# MAINTAINABILITY ISSUE: Global state and magic numbers
MAX_RETRIES = 3
TIMEOUT = 30
CONFIG = {'debug': True, 'log_level': 'DEBUG'}  # SECURITY: Debug mode enabled


def make_request_unsafe(endpoint, data):
    """
    SECURITY ISSUE: No SSL/TLS validation
    CODE QUALITY ISSUE: No timeout handling
    BEST PRACTICES ISSUE: Missing authentication headers
    """
    import requests
    
    # Global constants mixed with hardcoded values
    response = requests.post(
        f"http://example.com/{endpoint}",  # SECURITY: Using HTTP instead of HTTPS
        data=data,
        verify=False,
        headers={'Authorization': 'Bearer ' + API_KEY}  # SECURITY: Key in code
    )
    
    return response.json()


# BEST PRACTICES ISSUE: Module-level code execution with side effects
if __name__ == '__main__':
    processor = UserDataProcessor()
    
    # Test with intentional vulnerabilities
    user_data = processor.query_user("1'; DROP TABLE users; --")
    command_output = processor.execute_user_command("ls -la")
    
    # SECURITY ISSUE: Credentials logged
    print(f"Connecting with password: {DB_PASSWORD}")
