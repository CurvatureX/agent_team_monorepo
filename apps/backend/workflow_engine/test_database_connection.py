#!/usr/bin/env python3
"""
Test database connection using existing database.py configuration
基于现有database.py文件的数据库连接测试
"""

import time
from workflow_engine.models.database import test_db_connection, init_db, get_db_session
from workflow_engine.core.config import get_settings

def test_database_with_existing_config():
    """使用现有配置测试数据库连接"""
    print("🚀 Testing Database Connection with Existing Configuration")
    print("=" * 60)
    
    # 获取配置
    settings = get_settings()
    print(f"📋 Database URL: {settings.database_url[:50]}..." if len(settings.database_url) > 50 else f"📋 Database URL: {settings.database_url}")
    print(f"🔧 SSL Mode: {settings.database_ssl_mode}")
    print(f"🔧 Pool Size: {settings.database_pool_size}")
    print(f"🔧 Pool Timeout: {settings.database_pool_timeout}")
    
    # 测试连接
    print("\n🔌 Testing database connection...")
    start_time = time.time()
    
    try:
        success = test_db_connection()
        end_time = time.time()
        
        if success:
            print(f"✅ Database connection successful! Time: {end_time - start_time:.2f}s")
            
            # 测试会话
            print("\n📝 Testing database session...")
            try:
                db = get_db_session()
                result = db.execute("SELECT current_database(), current_user, version()")
                row = result.fetchone()
                print(f"✅ Session test successful:")
                print(f"   Database: {row[0]}")
                print(f"   User: {row[1]}")
                print(f"   Version: {row[2]}")
                db.close()
            except Exception as e:
                print(f"❌ Session test failed: {e}")
            
            # 测试初始化
            print("\n🏗️ Testing database initialization...")
            try:
                init_db()
                print("✅ Database initialization successful")
            except Exception as e:
                print(f"❌ Database initialization failed: {e}")
                
        else:
            print(f"❌ Database connection failed! Time: {end_time - start_time:.2f}s")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    
    return success

def test_database_operations():
    """测试数据库操作"""
    print("\n" + "=" * 60)
    print("🗄️ Testing Database Operations")
    print("=" * 60)
    
    try:
        db = get_db_session()
        
        # 测试基本查询
        print("📊 Testing basic queries...")
        
        # 检查表是否存在
        result = db.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in result.fetchall()]
        print(f"✅ Found {len(tables)} tables: {tables}")
        
        # 测试事务
        print("\n💾 Testing transaction...")
        try:
            # 开始事务
            db.begin()
            
            # 执行测试查询
            result = db.execute("SELECT 1 as test_value")
            test_value = result.fetchone()[0]
            print(f"✅ Transaction test successful: {test_value}")
            
            # 提交事务
            db.commit()
            print("✅ Transaction committed successfully")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Transaction failed, rolled back: {e}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        return False

def main():
    """主测试函数"""
    print("🎯 Workflow Engine Database Connection Test")
    print("=" * 60)
    
    # 测试基本连接
    connection_success = test_database_with_existing_config()
    
    if connection_success:
        # 测试数据库操作
        operations_success = test_database_operations()
        
        print("\n" + "=" * 60)
        print("🏁 Test Summary")
        print("=" * 60)
        print(f"✅ Connection Test: {'PASSED' if connection_success else 'FAILED'}")
        print(f"✅ Operations Test: {'PASSED' if operations_success else 'FAILED'}")
        
        if connection_success and operations_success:
            print("\n🎉 All tests passed! Database is ready for use.")
            return True
        else:
            print("\n⚠️ Some tests failed. Please check the configuration.")
            return False
    else:
        print("\n❌ Connection test failed. Cannot proceed with operations test.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 