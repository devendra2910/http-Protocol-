#!/usr/bin/env python3
"""
Complete HTTP/HTTPS Server with SSL/TLS support
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import ssl
import os
import threading
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
import time

class Database:
    """Simple in-memory database"""
    def __init__(self):
        self.users = {}
        self.posts = {}
        self.next_user_id = 1
        self.next_post_id = 1
    
    def create_user(self, name: str, email: str, age: Optional[int] = None) -> Dict[str, Any]:
        user_id = self.next_user_id
        user = {
            "id": user_id,
            "name": name,
            "email": email,
            "age": age,
            "created_at": time.time()
        }
        self.users[user_id] = user
        self.next_user_id += 1
        return user
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.users.get(user_id)
    
    def get_all_users(self) -> list:
        return list(self.users.values())
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if user_id not in self.users:
            return None
        self.users[user_id].update(updates)
        return self.users[user_id]
    
    def delete_user(self, user_id: int) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False
    
    def create_post(self, title: str, content: str, author_id: int) -> Optional[Dict[str, Any]]:
        if author_id not in self.users:
            return None
        
        post_id = self.next_post_id
        post = {
            "id": post_id,
            "title": title,
            "content": content,
            "author_id": author_id,
            "created_at": time.time()
        }
        self.posts[post_id] = post
        self.next_post_id += 1
        return post
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        return self.posts.get(post_id)
    
    def get_all_posts(self) -> list:
        return list(self.posts.values())
    
    def get_user_posts(self, user_id: int) -> list:
        return [post for post in self.posts.values() if post['author_id'] == user_id]

class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler with REST API support"""
    
    def __init__(self, *args, **kwargs):
        self.db = Database()
        super().__init__(*args, **kwargs)
    
    def _set_headers(self, status_code: int = 200, content_type: str = 'application/json'):
        """Set HTTP headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def _parse_path(self) -> tuple:
        """Parse URL path into components"""
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split('/') if p]
        return path_parts, parse_qs(parsed.query)
    
    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        """Read and parse JSON request body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return None
        
        try:
            body = self.rfile.read(content_length)
            return json.loads(body.decode('utf-8'))
        except:
            return None
    
    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response"""
        self._set_headers(status_code)
        response = json.dumps(data, indent=2).encode('utf-8')
        self.wfile.write(response)
    
    def _send_error(self, message: str, status_code: int = 400):
        """Send error response"""
        self._send_json_response({
            "success": False,
            "error": message,
            "timestamp": time.time()
        }, status_code)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._set_headers(200)
    
    def do_GET(self):
        """Handle GET requests"""
        path_parts, query_params = self._parse_path()
        
        try:
            # Root endpoint
            if not path_parts:
                self._send_json_response({
                    "success": True,
                    "message": "HTTP Server is running!",
                    "version": "1.0.0",
                    "endpoints": {
                        "GET /": "Server info",
                        "GET /users": "Get all users",
                        "GET /users/{id}": "Get user by ID",
                        "POST /users": "Create user",
                        "PUT /users/{id}": "Update user",
                        "DELETE /users/{id}": "Delete user",
                        "GET /posts": "Get all posts",
                        "GET /posts/{id}": "Get post by ID",
                        "POST /posts": "Create post",
                        "GET /users/{id}/posts": "Get user posts"
                    }
                })
                return
            
            # Users endpoints
            elif path_parts[0] == 'users':
                if len(path_parts) == 1:
                    # GET /users
                    users = self.db.get_all_users()
                    self._send_json_response({
                        "success": True,
                        "data": users,
                        "count": len(users)
                    })
                
                elif len(path_parts) == 2:
                    # GET /users/{id}
                    try:
                        user_id = int(path_parts[1])
                        user = self.db.get_user(user_id)
                        if user:
                            self._send_json_response({
                                "success": True,
                                "data": user
                            })
                        else:
                            self._send_error("User not found", 404)
                    except ValueError:
                        self._send_error("Invalid user ID")
                
                elif len(path_parts) == 3 and path_parts[2] == 'posts':
                    # GET /users/{id}/posts
                    try:
                        user_id = int(path_parts[1])
                        posts = self.db.get_user_posts(user_id)
                        self._send_json_response({
                            "success": True,
                            "data": posts,
                            "count": len(posts)
                        })
                    except ValueError:
                        self._send_error("Invalid user ID")
            
            # Posts endpoints
            elif path_parts[0] == 'posts':
                if len(path_parts) == 1:
                    # GET /posts
                    posts = self.db.get_all_posts()
                    self._send_json_response({
                        "success": True,
                        "data": posts,
                        "count": len(posts)
                    })
                
                elif len(path_parts) == 2:
                    # GET /posts/{id}
                    try:
                        post_id = int(path_parts[1])
                        post = self.db.get_post(post_id)
                        if post:
                            self._send_json_response({
                                "success": True,
                                "data": post
                            })
                        else:
                            self._send_error("Post not found", 404)
                    except ValueError:
                        self._send_error("Invalid post ID")
            
            else:
                self._send_error("Endpoint not found", 404)
        
        except Exception as e:
            self._send_error(f"Server error: {str(e)}", 500)
    
    def do_POST(self):
        """Handle POST requests"""
        path_parts, _ = self._parse_path()
        data = self._read_json_body()
        
        if data is None:
            self._send_error("Invalid JSON data")
            return
        
        try:
            # Create user
            if path_parts and path_parts[0] == 'users' and len(path_parts) == 1:
                name = data.get('name')
                email = data.get('email')
                age = data.get('age')
                
                if not name or not email:
                    self._send_error("Name and email are required")
                    return
                
                user = self.db.create_user(name, email, age)
                self._send_json_response({
                    "success": True,
                    "message": "User created successfully",
                    "data": user
                }, 201)
            
            # Create post
            elif path_parts and path_parts[0] == 'posts' and len(path_parts) == 1:
                title = data.get('title')
                content = data.get('content')
                author_id = data.get('author_id')
                
                if not title or not content or not author_id:
                    self._send_error("Title, content, and author_id are required")
                    return
                
                post = self.db.create_post(title, content, author_id)
                if post:
                    self._send_json_response({
                        "success": True,
                        "message": "Post created successfully",
                        "data": post
                    }, 201)
                else:
                    self._send_error("Author not found", 404)
            
            else:
                self._send_error("Endpoint not found", 404)
        
        except Exception as e:
            self._send_error(f"Server error: {str(e)}", 500)
    
    def do_PUT(self):
        """Handle PUT requests"""
        path_parts, _ = self._parse_path()
        data = self._read_json_body()
        
        if data is None:
            self._send_error("Invalid JSON data")
            return
        
        try:
            # Update user
            if path_parts and path_parts[0] == 'users' and len(path_parts) == 2:
                try:
                    user_id = int(path_parts[1])
                    updated_user = self.db.update_user(user_id, data)
                    if updated_user:
                        self._send_json_response({
                            "success": True,
                            "message": "User updated successfully",
                            "data": updated_user
                        })
                    else:
                        self._send_error("User not found", 404)
                except ValueError:
                    self._send_error("Invalid user ID")
            
            else:
                self._send_error("Endpoint not found", 404)
        
        except Exception as e:
            self._send_error(f"Server error: {str(e)}", 500)
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        path_parts, _ = self._parse_path()
        
        try:
            # Delete user
            if path_parts and path_parts[0] == 'users' and len(path_parts) == 2:
                try:
                    user_id = int(path_parts[1])
                    success = self.db.delete_user(user_id)
                    if success:
                        self._send_json_response({
                            "success": True,
                            "message": "User deleted successfully"
                        })
                    else:
                        self._send_error("User not found", 404)
                except ValueError:
                    self._send_error("Invalid user ID")
            
            else:
                self._send_error("Endpoint not found", 404)
        
        except Exception as e:
            self._send_error(f"Server error: {str(e)}", 500)

class HTTPSServer:
    """HTTPS Server with SSL/TLS support"""
    
    def __init__(self, host: str = 'localhost', port: int = 8443, 
                 certfile: str = 'server.crt', keyfile: str = 'server.key'):
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.server = None
    
    def generate_self_signed_cert(self):
        """Generate self-signed SSL certificate"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate file
        with open(self.certfile, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key file
        with open(self.keyfile, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        
        print(f"✅ Generated self-signed certificate: {self.certfile}")
        print(f"✅ Generated private key: {self.keyfile}")
    
    def start(self, use_https: bool = True):
        """Start the server"""
        self.server = HTTPServer((self.host, self.port), HTTPRequestHandler)
        
        if use_https:
            # Generate certificates if they don't exist
            if not os.path.exists(self.certfile) or not os.path.exists(self.keyfile):
                print("🔐 Generating SSL certificates...")
                self.generate_self_signed_cert()
            
            # Configure SSL context
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Wrap socket with SSL
            self.server.socket = ssl_context.wrap_socket(
                self.server.socket, 
                server_side=True
            )
            
            protocol = "HTTPS"
            url = f"https://{self.host}:{self.port}"
        else:
            protocol = "HTTP"
            url = f"http://{self.host}:{self.port}"
        
        print(f"🚀 Starting {protocol} Server...")
        print(f"📡 Server running on: {url}")
        print(f"🔧 Protocol: {protocol}")
        print(f"🏠 Host: {self.host}")
        print(f"🎯 Port: {self.port}")
        print("⏹️  Press Ctrl+C to stop the server\n")
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        finally:
            self.server.server_close()

def main():
    """Main function to start the server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HTTP/HTTPS Server')
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=8443, help='Server port (default: 8443)')
    parser.add_argument('--http', action='store_true', help='Use HTTP instead of HTTPS')
    parser.add_argument('--cert', default='server.crt', help='SSL certificate file')
    parser.add_argument('--key', default='server.key', help='SSL private key file')
    
    args = parser.parse_args()
    
    server = HTTPSServer(
        host=args.host,
        port=args.port,
        certfile=args.cert,
        keyfile=args.key
    )
    
    server.start(use_https=not args.http)

if __name__ == '__main__':
    main()
