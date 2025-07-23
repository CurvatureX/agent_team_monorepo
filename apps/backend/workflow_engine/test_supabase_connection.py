#!/usr/bin/env python3
"""
Comprehensive Supabase Database Connection Test
测试Supabase数据库连接的各种方式
"""

import psycopg2
import time
import socket
import ssl
from urllib.parse import urlparse, parse_qs
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

def get_database_url():
    """从.env文件获取数据库URL"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        return None
    return database_url

def test_dns_resolution(hostname):
    """测试DNS解析"""
    print(f"🔍 Testing DNS resolution for: {hostname}")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS resolution successful: {hostname} -> {ip}")
        return ip
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return None

def test_port_connectivity(hostname, port, timeout=5):
    """测试端口连接性"""
    print(f"🔌 Testing port connectivity: {hostname}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} is open and accessible")
            return True
        else:
            print(f"❌ Port {port} is not accessible (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Port connectivity test failed: {e}")
        return False

def test_ssl_connection(hostname, port, timeout=10):
    """测试SSL连接"""
    print(f"🔒 Testing SSL connection to: {hostname}:{port}")
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
        ssl_sock.connect((hostname, port))
        
        cert = ssl_sock.getpeercert()
        print(f"✅ SSL connection successful")
        print(f"   Certificate subject: {cert.get('subject', 'N/A')}")
        ssl_sock.close()
        return True
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
        return False

def test_database_connection(database_url, timeout=10):
    """测试数据库连接"""
    print(f"🗄️ Testing database connection...")
    
    try:
        # Parse the URL
        parsed = urlparse(database_url)
        query_params = parse_qs(parsed.query)
        
        print(f"   Host: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Database: {parsed.path[1:]}")
        print(f"   User: {parsed.username}")
        print(f"   SSL Mode: {query_params.get('sslmode', ['N/A'])[0]}")
        
        # Test connection using direct URI
        start_time = time.time()
        
        # 直接使用URI连接
        conn = psycopg2.connect(
            database_url,
            connect_timeout=timeout,
            application_name='workflow_engine_test'
        )
        
        end_time = time.time()
        print(f"✅ Database connection successful! Time: {end_time - start_time:.2f}s")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"   PostgreSQL version: {version[0]}")
        
        # Test current database
        cursor.execute("SELECT current_database(), current_user, inet_server_addr();")
        db_info = cursor.fetchone()
        print(f"   Current database: {db_info[0]}")
        print(f"   Current user: {db_info[1]}")
        print(f"   Server address: {db_info[2]}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed (OperationalError): {e}")
        return False
    except psycopg2.Error as e:
        print(f"❌ Database connection failed (PostgreSQL Error): {e}")
        return False
    except Exception as e:
        print(f"❌ Database connection failed (General Error): {e}")
        return False

def test_alternative_connection_strings():
    """测试不同的连接字符串格式"""
    print("\n🔄 Testing alternative connection strings...")
    
    # 从.env文件读取的原始连接字符串
    original_url = get_database_url()
    if not original_url:
        return
    
    # 测试不同的SSL模式
    ssl_modes = ['require', 'prefer', 'allow', 'disable']
    
    for ssl_mode in ssl_modes:
        if 'sslmode=' in original_url:
            test_url = original_url.replace('sslmode=require', f'sslmode={ssl_mode}')
        else:
            test_url = original_url + f"?sslmode={ssl_mode}"
        print(f"\n--- Testing with sslmode={ssl_mode} ---")
        test_database_connection(test_url, timeout=5)

def test_supabase_project_status():
    """测试Supabase项目状态"""
    print("\n📊 Testing Supabase project status...")
    
    database_url = get_database_url()
    if not database_url:
        return
    
    parsed = urlparse(database_url)
    hostname = parsed.hostname
    
    if 'supabase.co' in hostname:
        # 提取项目引用
        project_ref = hostname.replace('db.', '').replace('.supabase.co', '')
        main_domain = f"{project_ref}.supabase.co"
        db_domain = hostname
        
        print(f"Testing main domain: {main_domain}")
        main_ip = test_dns_resolution(main_domain)
        
        print(f"Testing database domain: {db_domain}")
        db_ip = test_dns_resolution(db_domain)
        
        if main_ip and not db_ip:
            print("⚠️  Main domain resolves but database domain doesn't")
            print("   This might indicate the Supabase project is paused or deleted")
        
        # 测试端口连接
        if db_ip:
            test_port_connectivity(db_ip, 5432)
            test_ssl_connection(db_ip, 5432)
    else:
        print(f"Testing hostname: {hostname}")
        ip = test_dns_resolution(hostname)
        if ip:
            test_port_connectivity(ip, parsed.port or 5432)
            test_ssl_connection(ip, parsed.port or 5432)

def main():
    """主测试函数"""
    print("🚀 Supabase Database Connection Test")
    print("=" * 50)
    
    # 获取数据库URL
    database_url = get_database_url()
    if not database_url:
        print("❌ No DATABASE_URL found in .env file")
        return
    
    print(f"📋 Using DATABASE_URL from .env file")
    print(f"   {database_url[:50]}..." if len(database_url) > 50 else f"   {database_url}")
    
    # 1. 测试项目状态
    test_supabase_project_status()
    
    # 2. 测试原始连接字符串
    print("\n" + "=" * 50)
    print("Testing database connection...")
    test_database_connection(database_url, timeout=15)
    
    # 3. 测试替代连接字符串
    test_alternative_connection_strings()
    
    print("\n" + "=" * 50)
    print("🏁 Connection test completed")
    
    # 提供建议
    print("\n💡 Recommendations:")
    print("1. Check if the database service is accessible")
    print("2. Verify the connection string format")
    print("3. Check if the database credentials are correct")
    print("4. Ensure network connectivity to the database host")

if __name__ == "__main__":
    main() 