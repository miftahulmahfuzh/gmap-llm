#!/usr/bin/env python3
"""
Simple HTTP server to serve the HTML frontend for the AI Places Finder.
Run this alongside your FastAPI backend server.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Configuration
PORT = 3000
DIRECTORY = "."  # Current directory


class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler with CORS support"""

    def end_headers(self):
        # Add CORS headers
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()


def main():
    """Main function to start the server"""

    # Change to the specified directory
    os.chdir(DIRECTORY)

    # Create the server
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        print(f"🌐 Starting HTML server...")
        print(f"📂 Serving directory: {os.getcwd()}")
        print(f"🔗 Server running at: http://localhost:{PORT}")
        print(f"📱 Frontend URL: http://localhost:{PORT}/index.html")
        print(f"🗺️  Make sure your FastAPI server is running on http://127.0.0.1:8000")
        print("\n⚡ To stop the server, press Ctrl+C")
        print("-" * 60)

        try:
            # Optionally open browser
            print("🚀 Opening browser...")
            webbrowser.open(f"http://localhost:{PORT}/index.html")
        except Exception as e:
            print(f"Could not open browser automatically: {e}")
            print("Please manually open http://localhost:{PORT}/index.html")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped by user")
            print("Goodbye! 👋")


if __name__ == "__main__":
    main()
