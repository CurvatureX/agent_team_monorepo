#!/usr/bin/env python3
"""
高级 Proto 管理工具
支持生成、验证、分发和版本管理 protobuf 文件
"""

import os
import sys
import subprocess
import shutil
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class ProtoManager:
    """高级 Protobuf 管理器"""
    
    def __init__(self):
        self.backend_root = Path.cwd()
        self.shared_proto_dir = self.backend_root / "shared" / "proto"
        self.api_gateway_proto_dir = self.backend_root / "api-gateway" / "proto"
        self.workflow_agent_root = self.backend_root / "workflow_agent"
        
        # 配置文件
        self.config_file = self.backend_root / "proto_config.json"
        self.load_config()
        
    def load_config(self):
        """加载配置"""
        default_config = {
            "proto_files": ["workflow_agent.proto"],
            "target_services": {
                "api-gateway": str(self.api_gateway_proto_dir),
                "workflow_agent": str(self.workflow_agent_root)
            },
            "version": "1.0.0",
            "last_update": None,
            "file_hashes": {}
        }
        
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = {**default_config, **json.load(f)}
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """保存配置"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        print("🔍 检查依赖...")
        
        # 检查 Python
        if not shutil.which("python"):
            print("❌ Python 未安装")
            return False
        
        # 检查 grpcio-tools
        try:
            import grpc_tools.protoc
            print("✅ grpcio-tools 已安装")
        except ImportError:
            print("⚠️ grpcio-tools 未安装，正在安装...")
            subprocess.run([sys.executable, "-m", "pip", "install", "grpcio-tools"], check=True)
            print("✅ grpcio-tools 安装完成")
        
        return True
    
    def detect_changes(self) -> List[str]:
        """检测 proto 文件变化"""
        changed_files = []
        
        for proto_file in self.config["proto_files"]:
            proto_path = self.shared_proto_dir / proto_file
            if not proto_path.exists():
                print(f"⚠️ Proto 文件不存在: {proto_path}")
                continue
            
            current_hash = self.calculate_file_hash(proto_path)
            stored_hash = self.config["file_hashes"].get(proto_file)
            
            if current_hash != stored_hash:
                changed_files.append(proto_file)
                print(f"📝 检测到变化: {proto_file}")
        
        return changed_files
    
    def generate_proto(self, proto_file: str) -> bool:
        """生成单个 proto 文件"""
        proto_path = self.shared_proto_dir / proto_file
        
        if not proto_path.exists():
            print(f"❌ Proto 文件不存在: {proto_path}")
            return False
        
        print(f"🔧 生成 {proto_file}...")
        
        try:
            # 生成到 shared/proto 目录
            cmd = [
                sys.executable, "-m", "grpc_tools.protoc",
                f"--python_out={self.shared_proto_dir}",
                f"--grpc_python_out={self.shared_proto_dir}",
                f"--proto_path={self.shared_proto_dir}",
                str(proto_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.backend_root)
            
            if result.returncode == 0:
                print(f"✅ {proto_file} 生成成功")
                return True
            else:
                print(f"❌ {proto_file} 生成失败:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 生成 {proto_file} 时出错: {e}")
            return False
    
    def distribute_files(self, proto_file: str) -> bool:
        """分发生成的文件到各个服务"""
        base_name = proto_file.replace('.proto', '')
        pb2_file = f"{base_name}_pb2.py"
        grpc_file = f"{base_name}_pb2_grpc.py"
        
        source_pb2 = self.shared_proto_dir / pb2_file
        source_grpc = self.shared_proto_dir / grpc_file
        
        if not source_pb2.exists() or not source_grpc.exists():
            print(f"❌ 生成的文件不存在: {pb2_file} 或 {grpc_file}")
            return False
        
        success = True
        for service_name, target_dir in self.config["target_services"].items():
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.copy2(source_pb2, target_path / pb2_file)
                shutil.copy2(source_grpc, target_path / grpc_file)
                print(f"✅ 已分发到 {service_name}")
            except Exception as e:
                print(f"❌ 分发到 {service_name} 失败: {e}")
                success = False
        
        return success
    
    def validate_generated_files(self, proto_file: str) -> bool:
        """验证生成的文件"""
        base_name = proto_file.replace('.proto', '')
        pb2_file = f"{base_name}_pb2.py"
        grpc_file = f"{base_name}_pb2_grpc.py"
        
        files_to_check = []
        
        # 检查 shared 目录
        files_to_check.extend([
            self.shared_proto_dir / pb2_file,
            self.shared_proto_dir / grpc_file
        ])
        
        # 检查各个服务目录
        for service_name, target_dir in self.config["target_services"].items():
            target_path = Path(target_dir)
            files_to_check.extend([
                target_path / pb2_file,
                target_path / grpc_file
            ])
        
        all_exist = True
        for file_path in files_to_check:
            if file_path.exists():
                print(f"✅ {file_path}")
            else:
                print(f"❌ 缺失: {file_path}")
                all_exist = False
        
        if all_exist:
            # 检查文件内容
            pb2_path = self.shared_proto_dir / pb2_file
            grpc_path = self.shared_proto_dir / grpc_file
            
            try:
                with open(pb2_path) as f:
                    pb2_content = f.read()
                with open(grpc_path) as f:
                    grpc_content = f.read()
                
                # 基本内容验证
                if "pb2" in pb2_content and "Servicer" in grpc_content:
                    print("✅ 文件内容验证通过")
                    return True
                else:
                    print("❌ 文件内容验证失败")
                    return False
                    
            except Exception as e:
                print(f"❌ 文件内容验证出错: {e}")
                return False
        
        return all_exist
    
    def update_file_hashes(self):
        """更新文件哈希记录"""
        for proto_file in self.config["proto_files"]:
            proto_path = self.shared_proto_dir / proto_file
            if proto_path.exists():
                self.config["file_hashes"][proto_file] = self.calculate_file_hash(proto_path)
        
        self.config["last_update"] = datetime.now().isoformat()
        self.save_config()
    
    def show_status(self):
        """显示状态信息"""
        print("\n📊 Proto 管理状态")
        print("=" * 50)
        print(f"版本: {self.config['version']}")
        print(f"最后更新: {self.config['last_update'] or '从未更新'}")
        print(f"Proto 文件数: {len(self.config['proto_files'])}")
        print(f"目标服务数: {len(self.config['target_services'])}")
        
        print("\n📁 Proto 文件:")
        for proto_file in self.config["proto_files"]:
            proto_path = self.shared_proto_dir / proto_file
            status = "✅ 存在" if proto_path.exists() else "❌ 缺失"
            print(f"  {proto_file}: {status}")
        
        print("\n🎯 目标服务:")
        for service_name, target_dir in self.config["target_services"].items():
            status = "✅ 存在" if Path(target_dir).exists() else "❌ 缺失"
            print(f"  {service_name}: {target_dir} ({status})")
    
    def run_full_update(self, force: bool = False):
        """运行完整更新"""
        print("🚀 开始 Proto 完整更新")
        print("=" * 50)
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 检测变化
        if not force:
            changed_files = self.detect_changes()
            if not changed_files:
                print("✅ 没有检测到 Proto 文件变化")
                return True
        else:
            changed_files = self.config["proto_files"]
            print("🔄 强制更新所有文件")
        
        # 处理每个变化的文件
        all_success = True
        for proto_file in changed_files:
            print(f"\n处理 {proto_file}...")
            
            # 生成
            if not self.generate_proto(proto_file):
                all_success = False
                continue
            
            # 分发
            if not self.distribute_files(proto_file):
                all_success = False
                continue
            
            # 验证
            if not self.validate_generated_files(proto_file):
                all_success = False
                continue
        
        if all_success:
            # 更新哈希记录
            self.update_file_hashes()
            print("\n🎉 Proto 更新完成！")
            print("\n📝 下一步:")
            print("  1. 重启相关服务")
            print("  2. 运行集成测试")
            print("  3. 验证功能正常")
        else:
            print("\n❌ 部分文件更新失败，请检查错误信息")
        
        return all_success

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="高级 Proto 管理工具")
    parser.add_argument("--force", "-f", action="store_true", help="强制更新所有文件")
    parser.add_argument("--status", "-s", action="store_true", help="显示状态信息")
    parser.add_argument("--validate", "-v", action="store_true", help="仅验证文件")
    
    args = parser.parse_args()
    
    manager = ProtoManager()
    
    if args.status:
        manager.show_status()
    elif args.validate:
        for proto_file in manager.config["proto_files"]:
            manager.validate_generated_files(proto_file)
    else:
        manager.run_full_update(force=args.force)

if __name__ == "__main__":
    main()