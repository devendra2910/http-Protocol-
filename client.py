#!/usr/bin/env python3
"""
Complete HTTP/HTTPS Client with SSL/TLS support
"""
import requests
import json
import ssl
import os
import time
from typing import Dict, Any, Optional, List
import urllib3
from pathlib import Path

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HTTPClient:
    """
    Comprehensive HTTP/HTTPS client with SSL/TLS support
    """
    
    def __init__(self, base_url: str, verify_ssl: bool = False, cert_file: str = None):
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.cert_file = cert_file
        self.session = requests.Session()
        
        # Configure SSL settings
        if not verify_ssl:
            self.session.verify = False
        elif cert_file and os.path.exists(cert_file):
            self.session.verify = cert_file
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SecureHTTPClient/1.0',
            'Accept': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                 params: Dict[str, Any] = None, timeout: int = 10) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=timeout,
                verify=self.session.verify
            )
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            # Add status information
            response_data.update({
                "_status_code": response.status_code,
                "_success": response.status_code < 400
            })
            
            return response_data
            
        except requests.exceptions.SSLError as e:
            return {
                "success": False,
                "error": f"SSL Error: {str(e)}",
                "suggestion": "Try using --no-verify-ssl or provide correct certificate"
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection Error: {str(e)}",
                "suggestion": "Check if server is running and URL is correct"
            }
        except requests.exceptions.Timeout as e:
            return {
                "success": False,
                "error": f"Timeout Error: {str(e)}",
                "suggestion": "Increase timeout or check network connection"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Request Error: {str(e)}"
            }
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return self._request('GET', '')
    
    def create_user(self, name: str, email: str, age: Optional[int] = None) -> Dict[str, Any]:
        """Create a new user"""
        data = {"name": name, "email": email}
        if age is not None:
            data["age"] = age
        return self._request('POST', 'users', data=data)
    
    def get_all_users(self) -> Dict[str, Any]:
        """Get all users"""
        return self._request('GET', 'users')
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID"""
        return self._request('GET', f'users/{user_id}')
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user"""
        return self._request('PUT', f'users/{user_id}', data=updates)
    
    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Delete user"""
        return self._request('DELETE', f'users/{user_id}')
    
    def create_post(self, title: str, content: str, author_id: int) -> Dict[str, Any]:
        """Create a new post"""
        data = {
            "title": title,
            "content": content,
            "author_id": author_id
        }
        return self._request('POST', 'posts', data=data)
    
    def get_all_posts(self) -> Dict[str, Any]:
        """Get all posts"""
        return self._request('GET', 'posts')
    
    def get_post(self, post_id: int) -> Dict[str, Any]:
        """Get post by ID"""
        return self._request('GET', f'posts/{post_id}')
    
    def get_user_posts(self, user_id: int) -> Dict[str, Any]:
        """Get all posts by a user"""
        return self._request('GET', f'users/{user_id}/posts')
    
    def close(self):
        """Close the session"""
        self.session.close()

class SecureHTTPClient(HTTPClient):
    """
    Enhanced HTTP client with security features and retry mechanism
    """
    
    def __init__(self, base_url: str, verify_ssl: bool = False, cert_file: str = None,
                 max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(base_url, verify_ssl, cert_file)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make request with retry logic"""
        for attempt in range(self.max_retries):
            result = self._request(method, endpoint, **kwargs)
            
            # Retry on connection errors or timeouts
            if (result.get('_status_code', 0) >= 500 or 
                'Connection Error' in str(result.get('error', '')) or
                'Timeout' in str(result.get('error', ''))):
                
                if attempt < self.max_retries - 1:
                    print(f"⚠️  Attempt {attempt + 1} failed, retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
            
            return result
        
        return result
    
    def health_check(self) -> bool:
        """Perform health check"""
        result = self.get_server_info()
        return result.get('_status_code', 0) == 200
    
    def download_certificate(self, save_path: str = "downloaded_server.crt") -> bool:
        """Download server certificate"""
        try:
            # Create a temporary session to get the certificate
            temp_session = requests.Session()
            response = temp_session.get(self.base_url, verify=False, timeout=5)
            
            if hasattr(response.raw, 'connection'):
                if hasattr(response.raw.connection, 'sock'):
                    sock = response.raw.connection.sock
                    if hasattr(sock, 'getpeercert'):
                        cert = sock.getpeercert(binary_form=True)
                        if cert:
                            with open(save_path, 'wb') as f:
                                f.write(cert)
                            print(f"✅ Certificate downloaded: {save_path}")
                            return True
            
            print("❌ Could not download certificate")
            return False
            
        except Exception as e:
            print(f"❌ Error downloading certificate: {e}")
            return False
        finally:
            temp_session.close()

def demo_secure_operations(client: SecureHTTPClient):
    """Demonstrate secure client operations"""
    print("\n" + "="*50)
    print("🔐 SECURE CLIENT DEMO")
    print("="*50)
    
    # Health check
    print("\n1. 🩺 Health Check...")
    is_healthy = client.health_check()
    print(f"   Server health: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    
    if not is_healthy:
        print("   ❌ Cannot proceed - server is not reachable")
        return
    
    # Server info
    print("\n2. 📊 Server Information...")
    server_info = client.get_server_info()
    if server_info.get('_success'):
        print(f"   ✅ {server_info.get('message', 'Connected successfully')}")
        print(f"   📍 Version: {server_info.get('version', 'Unknown')}")
    else:
        print(f"   ❌ Failed: {server_info.get('error', 'Unknown error')}")
    
    # Create users
    print("\n3. 👥 Creating Users...")
    users_data = [
        {"name": "Alice Johnson", "email": "alice@example.com", "age": 28},
        {"name": "Bob Smith", "email": "bob@example.com", "age": 32},
        {"name": "Charlie Brown", "email": "charlie@example.com", "age": 25}
    ]
    
    created_users = []
    for user_data in users_data:
        result = client.create_user(**user_data)
        if result.get('_success'):
            user_id = result.get('data', {}).get('id', 'Unknown')
            print(f"   ✅ Created user: {user_data['name']} (ID: {user_id})")
            created_users.append(result.get('data', {}))
        else:
            print(f"   ❌ Failed to create user {user_data['name']}: {result.get('error', 'Unknown error')}")
    
    # Get all users
    print("\n4. 📋 Getting All Users...")
    users_result = client.get_all_users()
    if users_result.get('_success'):
        users = users_result.get('data', [])
        print(f"   ✅ Retrieved {len(users)} users")
        for user in users:
            print(f"      👤 {user['name']} ({user['email']}) - ID: {user['id']}")
    else:
        print(f"   ❌ Failed to get users: {users_result.get('error', 'Unknown error')}")
    
    # Create posts
    print("\n5. 📝 Creating Posts...")
    if created_users:
        posts_data = [
            {"title": "First Post", "content": "This is my first post!", "author_id": created_users[0]['id']},
            {"title": "Second Post", "content": "Another interesting post!", "author_id": created_users[1]['id']},
            {"title": "Third Post", "content": "Yet another amazing post!", "author_id": created_users[0]['id']}
        ]
        
        for post_data in posts_data:
            result = client.create_post(**post_data)
            if result.get('_success'):
                post_id = result.get('data', {}).get('id', 'Unknown')
                print(f"   ✅ Created post: '{post_data['title']}' (ID: {post_id})")
            else:
                print(f"   ❌ Failed to create post: {result.get('error', 'Unknown error')}")
    
    # Get all posts
    print("\n6. 📰 Getting All Posts...")
    posts_result = client.get_all_posts()
    if posts_result.get('_success'):
        posts = posts_result.get('data', [])
        print(f"   ✅ Retrieved {len(posts)} posts")
        for post in posts:
            print(f"      📄 '{post['title']}' by User {post['author_id']}")
    
    # Get user posts
    print("\n7. 👤 Getting User Posts...")
    if created_users:
        user_posts_result = client.get_user_posts(created_users[0]['id'])
        if user_posts_result.get('_success'):
            user_posts = user_posts_result.get('data', [])
            print(f"   ✅ User {created_users[0]['name']} has {len(user_posts)} posts")
    
    # Update user
    print("\n8. ✏️  Updating User...")
    if created_users:
        update_result = client.update_user(created_users[0]['id'], {"name": "Alice Johnson-Updated", "age": 29})
        if update_result.get('_success'):
            print(f"   ✅ Updated user: {update_result.get('data', {}).get('name', 'Unknown')}")
    
    # Get specific user
    print("\n9. 🔍 Getting Specific User...")
    if created_users:
        user_result = client.get_user(created_users[0]['id'])
        if user_result.get('_success'):
            user = user_result.get('data', {})
            print(f"   ✅ User details: {user['name']}, {user['email']}, Age: {user.get('age', 'N/A')}")
    
    print("\n" + "="*50)
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("="*50)

def main():
    """Main function to run the client"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HTTP/HTTPS Client')
    parser.add_argument('--url', required=True, help='Server URL (e.g., https://localhost:8443)')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    parser.add_argument('--cert-file', help='SSL certificate file for verification')
    parser.add_argument('--download-cert', action='store_true', help='Download server certificate')
    parser.add_argument('--demo', action='store_true', help='Run demonstration')
    
    args = parser.parse_args()
    
    # Create client
    client = SecureHTTPClient(
        base_url=args.url,
        verify_ssl=not args.no_verify_ssl,
        cert_file=args.cert_file
    )
    
    try:
        # Download certificate if requested
        if args.download_cert:
            print("📥 Downloading server certificate...")
            client.download_certificate()
        
        # Run demo or single request
        if args.demo:
            demo_secure_operations(client)
        else:
            # Simple test
            print("🔍 Testing connection...")
            result = client.get_server_info()
            if result.get('_success'):
                print(f"✅ Connection successful: {result.get('message', 'Unknown')}")
                print(f"📊 Server version: {result.get('version', 'Unknown')}")
            else:
                print(f"❌ Connection failed: {result.get('error', 'Unknown error')}")
    
    except KeyboardInterrupt:
        print("\n🛑 Client stopped by user")
    finally:
        client.close()

if __name__ == '__main__':
    main()
