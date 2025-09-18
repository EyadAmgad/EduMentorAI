"""
Test file to verify class definition works
"""

import os
import sys
import django
from django.conf import settings

print("Starting test file...")

class TestProcessor:
    """Test class"""
    def __init__(self):
        self.name = "test"
    
    def process(self):
        return "processed"

print("Class defined:", TestProcessor)
print("Classes in globals:", [k for k, v in globals().items() if isinstance(v, type)])
