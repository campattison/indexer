import time
from datetime import datetime, timedelta

class AdaptiveRateLimiter:
    def __init__(self, initial_delay=1.0, max_delay=60.0):
        self.current_delay = initial_delay
        self.max_delay = max_delay
        self.last_request_time = None
        self.consecutive_errors = 0
        
    def wait_if_needed(self):
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.current_delay:
                time.sleep(self.current_delay - elapsed)
        self.last_request_time = time.time()
        
    def handle_success(self):
        self.consecutive_errors = 0
        self.current_delay = max(1.0, self.current_delay * 0.5)
        
    def handle_error(self, error_type):
        self.consecutive_errors += 1
        if "rate" in str(error_type).lower():
            self.current_delay = min(self.max_delay, self.current_delay * 2) 