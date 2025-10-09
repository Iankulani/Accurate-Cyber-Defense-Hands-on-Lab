import socket
import threading
import time
import requests
import json
import subprocess
import os
from datetime import datetime
import scapy.all as scapy
from scapy.all import IP, TCP, UDP, ICMP
import logging
from typing import Dict, List, Set
import sys

class CyberSecurityMonitor:
    def __init__(self):
        self.monitored_ips = set()
        self.is_monitoring = False
        self.monitoring_thread = None
        self.command_history = []
        self.telegram_token = None
        self.telegram_chat_id = None
        self.log_file = "cybersecurity_logs.txt"
        self.threat_logs = []
        self.telegram_bot_running = False
        self.telegram_bot_thread = None
        self.last_update_id = 0
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger()
        
        self.setup_interface()

    def setup_interface(self):
        """Setup the orange-themed interface"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_banner()

    def print_banner(self):
        """Print the main banner"""
        banner = """
        \033[93m
        ╔══════════════════════════════════════════════════════════════╗
        ║                                                              ║
        ║                  ACCURATE CYBER DEFENSE                      ║
        ║                                                              ║
        ║           community:                                         ║
        ║                                                              ║
        ╚══════════════════════════════════════════════════════════════╝
        \033[0m
        """
        print(banner)

    def print_orange(self, text):
        """Print text in orange color"""
        print(f"\033[93m{text}\033[0m")

    def print_red(self, text):
        """Print text in red color for warnings"""
        print(f"\033[91m{text}\033[0m")

    def log_command(self, command):
        """Log command to history"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.command_history.append(f"{timestamp} - {command}")

    def send_telegram_message(self, message):
        """Send message via Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            self.print_red("Telegram not configured. Use 'config telegram token' and 'config telegram chat_id'")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Telegram error: {e}")
            return False

    def test_telegram_connection(self):
        """Test Telegram connection"""
        if not self.telegram_token or not self.telegram_chat_id:
            return "Telegram not configured. Please set token and chat ID first."
        
        try:
            self.print_orange("Testing Telegram connection...")
            url = f"https://api.telegram.org/bot{self.telegram_token}/getMe"
            response = requests.get(url)
            
            if response.status_code == 200:
                bot_info = response.json()
                bot_name = bot_info['result']['first_name']
                
                # Test sending a message
                test_msg = f"✅ Telegram connection test successful!\nBot: {bot_name}\nTime: {datetime.now()}"
                if self.send_telegram_message(test_msg):
                    return f"Telegram connection successful! Bot: {bot_name}"
                else:
                    return "Bot connected but failed to send message."
            else:
                return f"Telegram connection failed: {response.text}"
                
        except Exception as e:
            return f"Telegram connection error: {e}"

    def start_telegram_bot(self):
        """Start Telegram bot to receive commands"""
        if not self.telegram_token:
            return "Telegram token not configured!"
        
        if self.telegram_bot_running:
            return "Telegram bot is already running!"
        
        self.telegram_bot_running = True
        self.telegram_bot_thread = threading.Thread(target=self._telegram_bot_loop)
        self.telegram_bot_thread.daemon = True
        self.telegram_bot_thread.start()
        return "Telegram bot started! You can now send commands via Telegram."

    def stop_telegram_bot(self):
        """Stop Telegram bot"""
        self.telegram_bot_running = False
        return "Telegram bot stopped."

    def _telegram_bot_loop(self):
        """Main loop for Telegram bot"""
        while self.telegram_bot_running:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
                params = {"offset": self.last_update_id + 1, "timeout": 30}
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    updates = response.json()
                    if updates["ok"] and updates["result"]:
                        for update in updates["result"]:
                            self.last_update_id = update["update_id"]
                            
                            if "message" in update and "text" in update["message"]:
                                message = update["message"]
                                chat_id = message["chat"]["id"]
                                text = message["text"]
                                
                                # Only process if it's from the configured chat ID
                                if str(chat_id) == self.telegram_chat_id:
                                    self._process_telegram_command(chat_id, text)
                
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Telegram bot error: {e}")
                time.sleep(5)

    def _process_telegram_command(self, chat_id, command):
        """Process Telegram commands"""
        try:
            command = command.strip()
            parts = command.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            self.log_command(f"TELEGRAM: {command}")
            
            # Handle different command formats
            if cmd.startswith('/'):
                result = self.handle_telegram_command(cmd, args)
            else:
                # Handle natural language commands
                result = self.handle_natural_command(command)
            
            # Send response back to Telegram
            if len(str(result)) > 4096:  # Telegram message limit
                result = str(result)[:4000] + "\n... (message truncated)"
            
            self.send_telegram_message(f"🔧 Command: {command}\n\n📋 Result:\n{result}")
            
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            self.send_telegram_message(f"❌ {error_msg}")

    def handle_natural_command(self, command):
        """Handle natural language commands"""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ['ping', 'test connection']):
            ip = self._extract_ip(command)
            return self.ping_ip(ip) if ip else "Please specify an IP address"
            
        elif any(word in command_lower for word in ['scan', 'port scan']):
            ip = self._extract_ip(command)
            return f"Open ports: {self.scan_ports(ip)}" if ip else "Please specify an IP address"
            
        elif any(word in command_lower for word in ['location', 'where is']):
            ip = self._extract_ip(command)
            return self.get_ip_location(ip) if ip else "Please specify an IP address"
            
        elif any(word in command_lower for word in ['traceroute', 'trace route']):
            ip = self._extract_ip(command)
            protocol = 'tcp' if 'tcp' in command_lower else 'udp'
            return self.traceroute(ip, protocol) if ip else "Please specify an IP address"
            
        elif any(word in command_lower for word in ['monitor', 'start monitoring']):
            ip = self._extract_ip(command)
            return self.start_monitoring_ip(ip) if ip else "Please specify an IP address"
            
        elif any(word in command_lower for word in ['status', 'show status']):
            return self.show_status()
            
        elif any(word in command_lower for word in ['help', 'commands']):
            return self.show_telegram_help()
            
        else:
            return "Unknown command. Send '/help' for available commands."

    def _extract_ip(self, text):
        """Extract IP address from text"""
        import re
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        matches = re.findall(ip_pattern, text)
        return matches[0] if matches else None

    def ping_ip(self, ip):
        """Ping an IP address"""
        try:
            self.print_orange(f"Pinging {ip}...")
            result = subprocess.run(['ping', '-c', '4', ip] if os.name != 'nt' else ['ping', '-n', '4', ip],
                                  capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            return f"Ping error: {e}"

    def scan_ports(self, ip, start_port=1, end_port=1000, deep_scan=False):
        """Scan ports on an IP address"""
        self.print_orange(f"Scanning {ip} from port {start_port} to {end_port}...")
        open_ports = []
        
        def scan_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    open_ports.append(port)
                    try:
                        service = socket.getservbyport(port, 'tcp') if port <= 1000 else "Unknown"
                        self.print_orange(f"Port {port} ({service}) is open")
                    except:
                        self.print_orange(f"Port {port} is open")
            except:
                pass

        threads = []
        for port in range(start_port, end_port + 1):
            thread = threading.Thread(target=scan_port, args=(port,))
            threads.append(thread)
            thread.start()
            
            # Limit concurrent threads
            if len(threads) >= 100:
                for t in threads:
                    t.join()
                threads = []
        
        for t in threads:
            t.join()
            
        return open_ports

    def get_ip_location(self, ip):
        """Get geographical location of IP"""
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}")
            data = response.json()
            if data['status'] == 'success':
                return f"""
📍 IP Location Information:
• IP: {ip}
• Country: {data['country']}
• Region: {data['regionName']}
• City: {data['city']}
• ISP: {data['isp']}
• Latitude: {data['lat']}
• Longitude: {data['lon']}
• Timezone: {data['timezone']}
                """
            return "Location not found"
        except Exception as e:
            return f"Location error: {e}"

    def traceroute(self, ip, protocol='udp'):
        """Perform traceroute"""
        try:
            self.print_orange(f"Performing {protocol.upper()} traceroute to {ip}...")
            if os.name == 'nt':  # Windows
                result = subprocess.run(['tracert', ip], capture_output=True, text=True)
            else:  # Linux/Mac
                if protocol == 'tcp':
                    result = subprocess.run(['traceroute', '-T', ip], capture_output=True, text=True)
                else:
                    result = subprocess.run(['traceroute', ip], capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            return f"Traceroute error: {e}"

    def monitor_threats(self):
        """Monitor for cybersecurity threats"""
        while self.is_monitoring:
            for ip in list(self.monitored_ips):
                self.check_for_threats(ip)
            time.sleep(10)  # Check every 10 seconds

    def check_for_threats(self, ip):
        """Check for various cyber threats"""
        threats = []
        
        # Check for port scanning activity
        port_scan_result = self.detect_port_scan(ip)
        if port_scan_result:
            threats.append(port_scan_result)
            
        # Check for DOS/DDOS patterns
        dos_result = self.detect_dos_patterns(ip)
        if dos_result:
            threats.append(dos_result)
            
        # Log threats
        for threat in threats:
            log_entry = f"{datetime.now()} - THREAT DETECTED - {ip} - {threat}"
            self.threat_logs.append(log_entry)
            self.logger.warning(log_entry)
            
            # Send Telegram alert
            if self.telegram_token and self.telegram_chat_id:
                self.send_telegram_message(f"🚨 THREAT ALERT 🚨\nIP: {ip}\nThreat: {threat}")

    def detect_port_scan(self, ip):
        """Detect port scanning activity"""
        # Simulate port scan detection logic
        if len(self.threat_logs) > 10:  # Simple heuristic
            return "Possible port scanning detected"
        return None

    def detect_dos_patterns(self, ip):
        """Detect DOS/DDOS patterns"""
        # Simulate DOS detection logic
        return None  # Placeholder for actual implementation

    def view_logs(self):
        """View security logs"""
        try:
            with open(self.log_file, 'r') as f:
                return f.read()
        except:
            return "No logs available"

    def export_data(self):
        """Export data to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"security_export_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("CYBER SECURITY EXPORT DATA\n")
            f.write("=" * 50 + "\n")
            f.write(f"Export Time: {datetime.now()}\n\n")
            
            f.write("MONITORED IPS:\n")
            for ip in self.monitored_ips:
                f.write(f"- {ip}\n")
                
            f.write("\nTHREAT LOGS:\n")
            for log in self.threat_logs[-100:]:  # Last 100 entries
                f.write(f"{log}\n")
                
            f.write("\nCOMMAND HISTORY:\n")
            for cmd in self.command_history[-50:]:  # Last 50 commands
                f.write(f"{cmd}\n")
                
        return f"Data exported to {filename}"

    def handle_telegram_command(self, command, args):
        """Handle Telegram bot commands"""
        commands = {
            '/help': self.show_telegram_help,
            '/ping': lambda: self.ping_ip(args[0]) if args else "Usage: /ping [IP]",
            '/scan': lambda: f"Open ports: {self.scan_ports(args[0])}" if args else "Usage: /scan [IP]",
            '/deepscan': lambda: f"Open ports: {self.scan_ports(args[0], 1, 65535, True)}" if args else "Usage: /deepscan [IP]",
            '/location': lambda: self.get_ip_location(args[0]) if args else "Usage: /location [IP]",
            '/traceroute': lambda: self.traceroute(args[0]) if args else "Usage: /traceroute [IP]",
            '/tracert': lambda: self.traceroute(args[0]) if args else "Usage: /tracert [IP]",
            '/start_monitoring': lambda: self.start_monitoring_ip(args[0]) if args else "Usage: /start_monitoring [IP]",
            '/stop_monitoring': self.stop_monitoring,
            '/status': self.show_status,
            '/view_logs': lambda: self.view_logs(),
            '/history': lambda: "\n".join(self.command_history[-10:]) if self.command_history else "No history",
            '/test_telegram': self.test_telegram_connection,
            '/start_bot': self.start_telegram_bot,
            '/stop_bot': self.stop_telegram_bot,
        }
        
        if command in commands:
            return commands[command]()
        return "Unknown command. Send /help for available commands."

    def show_telegram_help(self):
        """Show Telegram-specific help menu"""
        help_text = """
🍊 CYBER SECURITY TOOL - TELEGRAM COMMANDS 🍊

🔍 Network Commands:
/ping [ip] - Ping an IP address
/scan [ip] - Scan common ports (1-1000)
/deepscan [ip] - Deep scan all ports (1-65535)
/location [ip] - Get IP geographical location
/traceroute [ip] - Perform traceroute
/tracert [ip] - Alias for traceroute

📊 Monitoring Commands:
/start_monitoring [ip] - Start monitoring IP for threats
/stop_monitoring - Stop all monitoring
/status - Show monitoring status
/view_logs - View security logs

🤖 Bot Control:
/test_telegram - Test Telegram connection
/start_bot - Start Telegram bot
/stop_bot - Stop Telegram bot
/history - View command history

💡 Natural Language Examples:
"ping 8.8.8.8"
"scan ports on 192.168.1.1"
"where is 142.251.16.78"
"traceroute to google.com"
"start monitoring 10.0.0.5"
        """
        return help_text

    def show_help(self):
        """Show full help menu"""
        help_text = """
🍊 CYBER SECURITY TOOL - COMMAND HELP 🍊

Basic Commands:
- help: Show this help message
- ping [ip]: Ping an IP address
- scan [ip]: Scan common ports (1-1000)
- deep_scan [ip]: Deep scan all ports (1-65535)
- location [ip]: Get IP geographical location
- traceroute [ip]: Perform traceroute
- tracert [ip]: Alias for traceroute

Monitoring Commands:
- start monitoring [ip]: Start monitoring IP for threats
- stop monitoring: Stop all monitoring
- status: Show monitoring status
- view: View security logs
- add [ip]: Add IP to monitoring list
- remove [ip]: Remove IP from monitoring list

Telegram Commands:
- config telegram token [token]: Set Telegram bot token
- config telegram chat_id [id]: Set Telegram chat ID
- test telegram: Test Telegram connection
- start telegram bot: Start Telegram bot
- stop telegram bot: Stop Telegram bot
- export: Export data to file

System Commands:
- history: View command history
- exit: Exit the program

Telegram Bot Commands (prefix with /):
/help, /ping, /scan, /deepscan, /location, /traceroute, /tracert
/start_monitoring, /stop_monitoring, /status, /view_logs, /history
/test_telegram, /start_bot, /stop_bot
        """
        return help_text

    def start_monitoring_ip(self, ip):
        """Start monitoring an IP address"""
        self.monitored_ips.add(ip)
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self.monitor_threats)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
        return f"Started monitoring {ip}"

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        self.monitored_ips.clear()
        return "Monitoring stopped"

    def show_status(self):
        """Show monitoring status"""
        status = f"""
📊 Monitoring Status: {'ACTIVE 🟢' if self.is_monitoring else 'INACTIVE 🔴'}
• Monitored IPs: {len(self.monitored_ips)}
• Threats Detected: {len(self.threat_logs)}
• Telegram Bot: {'RUNNING 🟢' if self.telegram_bot_running else 'STOPPED 🔴'}
• Telegram Configured: {'YES ✅' if self.telegram_token and self.telegram_chat_id else 'NO ❌'}

Monitored IP Addresses:
"""
        for ip in self.monitored_ips:
            status += f"• {ip}\n"
        
        if not self.monitored_ips:
            status += "• No IPs being monitored\n"
            
        return status

    def run(self):
        """Main program loop"""
        self.print_orange("Accurate Cyber Defense Hands on Lab Type 'help' for commands.")
        
        while True:
            try:
                command = input("\n\033[93maccurate-cyber-lab🍊>\033[0m ").strip()
                if not command:
                    continue
                    
                self.log_command(command)
                parts = command.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd == 'exit':
                    self.stop_monitoring()
                    self.stop_telegram_bot()
                    self.print_orange("Goodbye! Stay secure! 🍊")
                    break
                    
                elif cmd == 'help':
                    self.print_orange(self.show_help())
                    
                elif cmd == 'ping':
                    if args:
                        result = self.ping_ip(args[0])
                        self.print_orange(result)
                    else:
                        self.print_red("Usage: ping [IP]")
                        
                elif cmd == 'scan':
                    if args:
                        open_ports = self.scan_ports(args[0])
                        self.print_orange(f"Scan completed. Open ports: {open_ports}")
                    else:
                        self.print_red("Usage: scan [IP]")
                        
                elif cmd == 'deep_scan':
                    if args:
                        self.print_orange("Starting deep scan (this may take a while)...")
                        open_ports = self.scan_ports(args[0], 1, 65535, True)
                        self.print_orange(f"Deep scan completed. Open ports: {open_ports}")
                    else:
                        self.print_red("Usage: deep_scan [IP]")
                        
                elif cmd in ['location', 'whereis']:
                    if args:
                        result = self.get_ip_location(args[0])
                        self.print_orange(result)
                    else:
                        self.print_red("Usage: location [IP]")
                        
                elif cmd in ['traceroute', 'tracert']:
                    if args:
                        protocol = 'tcp' if cmd == 'traceroute' else 'udp'
                        result = self.traceroute(args[0], protocol)
                        self.print_orange(result)
                    else:
                        self.print_red(f"Usage: {cmd} [IP]")
                        
                elif cmd == 'start':
                    if len(args) > 1 and args[0] == 'monitoring':
                        if len(args) > 1:
                            result = self.start_monitoring_ip(args[1])
                            self.print_orange(result)
                        else:
                            self.print_red("Usage: start monitoring [IP]")
                    elif len(args) > 1 and args[0] == 'telegram' and args[1] == 'bot':
                        result = self.start_telegram_bot()
                        self.print_orange(result)
                    else:
                        self.print_red("Usage: start monitoring [IP] or start telegram bot")
                        
                elif cmd == 'stop':
                    if len(args) > 0 and args[0] == 'monitoring':
                        result = self.stop_monitoring()
                        self.print_orange(result)
                    elif len(args) > 1 and args[0] == 'telegram' and args[1] == 'bot':
                        result = self.stop_telegram_bot()
                        self.print_orange(result)
                    else:
                        self.print_red("Usage: stop monitoring or stop telegram bot")
                    
                elif cmd == 'status':
                    result = self.show_status()
                    self.print_orange(result)
                    
                elif cmd == 'view':
                    result = self.view_logs()
                    self.print_orange(result)
                    
                elif cmd == 'add':
                    if args:
                        self.monitored_ips.add(args[0])
                        self.print_orange(f"Added {args[0]} to monitoring list")
                    else:
                        self.print_red("Usage: add [IP]")
                        
                elif cmd == 'remove':
                    if args:
                        if args[0] in self.monitored_ips:
                            self.monitored_ips.remove(args[0])
                            self.print_orange(f"Removed {args[0]} from monitoring list")
                        else:
                            self.print_red("IP not in monitoring list")
                    else:
                        self.print_red("Usage: remove [IP]")
                        
                elif cmd == 'history':
                    self.print_orange("Command History:")
                    for i, cmd in enumerate(self.command_history[-10:], 1):
                        self.print_orange(f"{i}. {cmd}")
                        
                elif cmd == 'config' and len(args) > 2:
                    if args[0] == 'telegram':
                        if args[1] == 'token':
                            self.telegram_token = args[2]
                            self.print_orange("Telegram token configured")
                        elif args[1] == 'chat_id':
                            self.telegram_chat_id = args[2]
                            self.print_orange("Telegram chat ID configured")
                        else:
                            self.print_red("Usage: config telegram [token|chat_id] [value]")
                    else:
                        self.print_red("Usage: config telegram [token|chat_id] [value]")
                        
                elif cmd == 'test' and len(args) > 0 and args[0] == 'telegram':
                    result = self.test_telegram_connection()
                    self.print_orange(result)
                    
                elif cmd == 'export':
                    result = self.export_data()
                    self.print_orange(result)
                    
                else:
                    self.print_red("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                self.print_orange("\nGoodbye! Stay secure! 🍊")
                break
            except Exception as e:
                self.print_red(f"Error: {e}")

def main():
    """Main function"""
    # Check if running as root for some network operations
    if os.name != 'nt' and os.geteuid() != 0:
        print("\033[93mWarning: Some features may require root privileges\033[0m")
    
    monitor = CyberSecurityMonitor()
    monitor.run()

if __name__ == "__main__":
    main()