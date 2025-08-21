"""
Notion API适配器
实现Notion API的统一调用接口，使用Notion SDK
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import json

from .base import APIAdapter, OAuth2Config, PermanentError, TemporaryError, ValidationError, register_adapter

# Import Notion SDK
try:
    from ...sdks.notion_sdk import (
        NotionSDK,
        NotionError,
        NotionAuthError,
        NotionPermissionError,
        NotionNotFoundError,
        NotionValidationError,
        NotionRateLimitError,
        Block,
        RichText,
    )
    NOTION_SDK_AVAILABLE = True
except ImportError:
    NOTION_SDK_AVAILABLE = False
    logger.warning("Notion SDK not available, adapter will use direct HTTP calls")

logger = logging.getLogger(__name__)


@register_adapter("notion")
class NotionAdapter(APIAdapter):
    """Notion API适配器
    
    支持的操作:
    - list_databases: 列出所有数据库
    - query_database: 查询数据库内容
    - create_page: 创建新页面
    - get_page: 获取页面详情
    - update_page: 更新页面属性
    - archive_page: 归档/删除页面
    - get_blocks: 获取页面块内容
    - append_blocks: 添加内容块到页面
    - search: 全局搜索
    - list_users: 列出工作区用户
    """
    
    # Notion API基础URL
    BASE_URL = "https://api.notion.com/v1"
    
    # Notion API版本 - 使用最新稳定版本
    API_VERSION = "2022-06-28"
    
    # 支持的操作定义
    OPERATIONS = {
        # 数据库操作
        "list_databases": "列出所有数据库",
        "query_database": "查询数据库内容",
        "create_database": "创建新数据库",
        "retrieve_database": "获取数据库详情",
        
        # 页面操作
        "create_page": "创建新页面",
        "get_page": "获取页面详情",
        "update_page": "更新页面属性",
        "archive_page": "归档页面",
        
        # 块操作
        "get_blocks": "获取页面块内容",
        "append_blocks": "添加内容块",
        "update_block": "更新块内容",
        "delete_block": "删除块",
        
        # 搜索
        "search": "全局搜索",
        
        # 用户
        "list_users": "列出工作区用户",
        "get_user": "获取用户信息"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_name = "notion"
    
    def get_oauth2_config(self) -> OAuth2Config:
        """获取Notion OAuth2配置
        
        注意: Notion不使用传统的scope系统
        """
        return OAuth2Config(
            client_id="",  # 将从环境变量或配置中加载
            client_secret="",  # 将从环境变量或配置中加载
            auth_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            revoke_url=None,  # Notion不支持token撤销
            scopes=[],  # Notion不使用scope
            redirect_uri="http://localhost:8000/auth/notion/callback"
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证Notion凭证"""
        required_fields = ["access_token"]
        return all(field in credentials and credentials[field] for field in required_fields)
    
    async def call(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """统一的API调用接口，优先使用SDK"""
        if not self.validate_credentials(credentials):
            raise ValidationError("Invalid credentials: missing access_token")
        
        if operation not in self.OPERATIONS:
            raise ValidationError(f"Unsupported operation: {operation}")
        
        # 如果SDK可用，使用SDK方式
        if NOTION_SDK_AVAILABLE:
            return await self._call_with_sdk(operation, parameters, credentials)
        else:
            # 降级到直接HTTP调用
            # 根据操作类型分发到具体的处理方法
            handler_mapping = {
                "list_databases": self._list_databases,
                "query_database": self._query_database,
                "create_database": self._create_database,
                "retrieve_database": self._retrieve_database,
                "create_page": self._create_page,
                "get_page": self._get_page,
                "update_page": self._update_page,
                "archive_page": self._archive_page,
                "get_blocks": self._get_blocks,
                "append_blocks": self._append_blocks,
                "update_block": self._update_block,
                "delete_block": self._delete_block,
                "search": self._search,
                "list_users": self._list_users,
                "get_user": self._get_user
            }
            
            handler = handler_mapping[operation]
            return await handler(parameters, credentials)
    
    async def _call_with_sdk(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """使用SDK执行Notion操作"""
        sdk = NotionSDK(access_token=credentials["access_token"])
        
        try:
            if operation == "list_databases":
                result = await sdk.list_databases(
                    page_size=parameters.get("page_size", 100),
                    start_cursor=parameters.get("start_cursor")
                )
                return {
                    "success": True,
                    "databases": [db.__dict__ for db in result.results if hasattr(db, 'id') and db.__class__.__name__ == 'Database'],
                    "has_more": result.has_more,
                    "next_cursor": result.next_cursor
                }
            
            elif operation == "query_database":
                result = await sdk.query_database(
                    database_id=parameters["database_id"],
                    filter=parameters.get("filter"),
                    sorts=parameters.get("sorts"),
                    page_size=parameters.get("page_size", 100),
                    start_cursor=parameters.get("start_cursor")
                )
                return {
                    "success": True,
                    "results": [page.__dict__ for page in result.pages],
                    "has_more": result.has_more,
                    "next_cursor": result.next_cursor
                }
            
            elif operation == "create_page":
                # 处理简化的参数
                children = None
                if parameters.get("content"):
                    children = [Block.paragraph(parameters["content"])]
                elif parameters.get("children"):
                    # 转换children为Block对象
                    children = []
                    for child in parameters["children"]:
                        if isinstance(child, dict):
                            block_type = child.get("type", "paragraph")
                            if block_type == "paragraph":
                                children.append(Block.paragraph(child.get("text", "")))
                            # 可以添加更多块类型
                
                page = await sdk.create_page(
                    parent=parameters.get("parent"),
                    database_id=parameters.get("database_id"),
                    properties=parameters.get("properties"),
                    children=children,
                    icon=parameters.get("icon"),
                    cover=parameters.get("cover")
                )
                return {
                    "success": True,
                    "page": page.__dict__,
                    "page_id": page.id,
                    "url": page.url
                }
            
            elif operation == "get_page":
                page = await sdk.get_page(parameters["page_id"])
                return {
                    "success": True,
                    "page": page.__dict__
                }
            
            elif operation == "update_page":
                page = await sdk.update_page(
                    page_id=parameters["page_id"],
                    properties=parameters.get("properties"),
                    icon=parameters.get("icon"),
                    cover=parameters.get("cover"),
                    archived=parameters.get("archived")
                )
                return {
                    "success": True,
                    "page": page.__dict__,
                    "page_id": page.id
                }
            
            elif operation == "archive_page":
                page = await sdk.archive_page(parameters["page_id"])
                return {
                    "success": True,
                    "message": "Page archived successfully",
                    "page_id": page.id,
                    "archived": page.archived
                }
            
            elif operation == "get_blocks":
                result = await sdk.get_blocks(
                    block_id=parameters.get("block_id") or parameters.get("page_id"),
                    page_size=parameters.get("page_size", 100),
                    start_cursor=parameters.get("start_cursor")
                )
                return {
                    "success": True,
                    "blocks": [block.__dict__ for block in result["blocks"]],
                    "has_more": result["has_more"],
                    "next_cursor": result.get("next_cursor")
                }
            
            elif operation == "append_blocks":
                # 转换children为Block对象
                children = []
                for child in parameters.get("children", []):
                    if isinstance(child, dict):
                        block_type = child.get("type", "paragraph")
                        if block_type == "paragraph":
                            children.append(Block.paragraph(child.get("text", "")))
                
                blocks = await sdk.append_blocks(
                    block_id=parameters.get("block_id") or parameters.get("page_id"),
                    children=children,
                    after=parameters.get("after")
                )
                return {
                    "success": True,
                    "blocks": [block.__dict__ for block in blocks]
                }
            
            elif operation == "search":
                result = await sdk.search(
                    query=parameters.get("query"),
                    filter=parameters.get("filter"),
                    sort=parameters.get("sort"),
                    page_size=parameters.get("page_size", 100),
                    start_cursor=parameters.get("start_cursor")
                )
                return {
                    "success": True,
                    "results": [item.__dict__ for item in result.results],
                    "has_more": result.has_more,
                    "next_cursor": result.next_cursor
                }
            
            elif operation == "list_users":
                result = await sdk.list_users(
                    page_size=parameters.get("page_size", 100),
                    start_cursor=parameters.get("start_cursor")
                )
                return {
                    "success": True,
                    "users": [user.__dict__ for user in result["users"]],
                    "has_more": result["has_more"],
                    "next_cursor": result.get("next_cursor")
                }
            
            elif operation == "get_user":
                user = await sdk.get_user(parameters["user_id"])
                return {
                    "success": True,
                    "user": user.__dict__
                }
            
            else:
                raise ValidationError(f"Operation {operation} not implemented in SDK mode")
        
        except NotionAuthError as e:
            raise ValidationError(f"Authentication failed: {str(e)}")
        except NotionPermissionError as e:
            raise PermanentError(f"Permission denied: {str(e)}")
        except NotionNotFoundError as e:
            raise PermanentError(f"Resource not found: {str(e)}")
        except NotionRateLimitError as e:
            raise TemporaryError(f"Rate limit exceeded: {str(e)}")
        except NotionValidationError as e:
            raise ValidationError(f"Validation error: {str(e)}")
        except NotionError as e:
            raise TemporaryError(f"Notion API error: {str(e)}")
        finally:
            await sdk.close()
    
    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """准备Notion API请求头
        
        覆盖父类方法以添加Notion特定的headers
        """
        headers = super()._prepare_headers(credentials)
        # 添加Notion API版本
        headers["Notion-Version"] = self.API_VERSION
        return headers
    
    async def _list_databases(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出所有数据库
        
        使用search API查找所有database类型的对象
        """
        search_params = {
            "filter": {"value": "database", "property": "object"},
            "page_size": parameters.get("page_size", 100)
        }
        
        if "start_cursor" in parameters:
            search_params["start_cursor"] = parameters["start_cursor"]
        
        url = f"{self.BASE_URL}/search"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=search_params
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        # 只返回数据库类型的结果
        databases = [item for item in data.get("results", []) if item.get("object") == "database"]
        
        return {
            "success": True,
            "databases": databases,
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
            "total_count": len(databases)
        }
    
    async def _query_database(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """查询数据库内容"""
        database_id = parameters.get("database_id")
        
        if not database_id:
            raise ValidationError("Missing required parameter: database_id")
        
        # 构建查询参数
        query_params = {}
        
        # 过滤条件
        if "filter" in parameters:
            query_params["filter"] = parameters["filter"]
        
        # 排序
        if "sorts" in parameters:
            query_params["sorts"] = parameters["sorts"]
        
        # 分页
        if "start_cursor" in parameters:
            query_params["start_cursor"] = parameters["start_cursor"]
        
        if "page_size" in parameters:
            query_params["page_size"] = min(int(parameters["page_size"]), 100)
        
        url = f"{self.BASE_URL}/databases/{database_id}/query"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=query_params
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        return {
            "success": True,
            "results": data.get("results", []),
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
            "total_count": len(data.get("results", []))
        }
    
    async def _create_database(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建新数据库"""
        # 验证必需参数
        if "parent" not in parameters:
            raise ValidationError("Missing required parameter: parent")
        
        if "title" not in parameters:
            raise ValidationError("Missing required parameter: title")
        
        # 构建数据库数据
        database_data = {
            "parent": parameters["parent"],
            "title": self._format_rich_text(parameters["title"]),
            "properties": parameters.get("properties", {})
        }
        
        # 可选参数
        if "description" in parameters:
            database_data["description"] = self._format_rich_text(parameters["description"])
        
        if "icon" in parameters:
            database_data["icon"] = parameters["icon"]
        
        if "cover" in parameters:
            database_data["cover"] = parameters["cover"]
        
        url = f"{self.BASE_URL}/databases"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=database_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        database = response.json()
        
        return {
            "success": True,
            "database": database,
            "database_id": database.get("id"),
            "url": database.get("url")
        }
    
    async def _retrieve_database(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取数据库详情"""
        database_id = parameters.get("database_id")
        
        if not database_id:
            raise ValidationError("Missing required parameter: database_id")
        
        url = f"{self.BASE_URL}/databases/{database_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        database = response.json()
        
        return {
            "success": True,
            "database": database
        }
    
    async def _create_page(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建新页面"""
        # 验证必需参数
        if "parent" not in parameters:
            # 如果提供了database_id，自动构建parent
            if "database_id" in parameters:
                parameters["parent"] = {"database_id": parameters["database_id"]}
            else:
                raise ValidationError("Missing required parameter: parent or database_id")
        
        # 构建页面数据
        page_data = {
            "parent": parameters["parent"]
        }
        
        # 添加属性
        if "properties" in parameters:
            page_data["properties"] = parameters["properties"]
        elif "title" in parameters:
            # 简化方式：只提供标题
            page_data["properties"] = {
                "title": {
                    "title": self._format_rich_text(parameters["title"])
                }
            }
        
        # 添加子块（内容）
        if "children" in parameters:
            page_data["children"] = parameters["children"]
        elif "content" in parameters:
            # 简化方式：将文本内容转换为段落块
            page_data["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._format_rich_text(parameters["content"])
                    }
                }
            ]
        
        # 可选参数
        if "icon" in parameters:
            page_data["icon"] = parameters["icon"]
        
        if "cover" in parameters:
            page_data["cover"] = parameters["cover"]
        
        url = f"{self.BASE_URL}/pages"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=page_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        page = response.json()
        
        return {
            "success": True,
            "page": page,
            "page_id": page.get("id"),
            "url": page.get("url")
        }
    
    async def _get_page(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取页面详情"""
        page_id = parameters.get("page_id")
        
        if not page_id:
            raise ValidationError("Missing required parameter: page_id")
        
        url = f"{self.BASE_URL}/pages/{page_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        page = response.json()
        
        return {
            "success": True,
            "page": page
        }
    
    async def _update_page(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新页面属性"""
        page_id = parameters.get("page_id")
        
        if not page_id:
            raise ValidationError("Missing required parameter: page_id")
        
        # 构建更新数据
        update_data = {}
        
        # 更新属性
        if "properties" in parameters:
            update_data["properties"] = parameters["properties"]
        
        # 更新图标
        if "icon" in parameters:
            update_data["icon"] = parameters["icon"]
        
        # 更新封面
        if "cover" in parameters:
            update_data["cover"] = parameters["cover"]
        
        # 归档状态
        if "archived" in parameters:
            update_data["archived"] = parameters["archived"]
        
        if not update_data:
            raise ValidationError("No fields to update specified")
        
        url = f"{self.BASE_URL}/pages/{page_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "PATCH", url, headers=headers, json_data=update_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        page = response.json()
        
        return {
            "success": True,
            "page": page,
            "page_id": page.get("id"),
            "updated_fields": list(update_data.keys())
        }
    
    async def _archive_page(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """归档页面（软删除）"""
        page_id = parameters.get("page_id")
        
        if not page_id:
            raise ValidationError("Missing required parameter: page_id")
        
        # 使用update_page设置archived为true
        update_data = {"archived": True}
        
        url = f"{self.BASE_URL}/pages/{page_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "PATCH", url, headers=headers, json_data=update_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        page = response.json()
        
        return {
            "success": True,
            "message": "Page archived successfully",
            "page_id": page_id,
            "archived": page.get("archived", True)
        }
    
    async def _get_blocks(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取页面块内容"""
        block_id = parameters.get("block_id") or parameters.get("page_id")
        
        if not block_id:
            raise ValidationError("Missing required parameter: block_id or page_id")
        
        # 构建查询参数
        query_params = {}
        
        if "start_cursor" in parameters:
            query_params["start_cursor"] = parameters["start_cursor"]
        
        if "page_size" in parameters:
            query_params["page_size"] = min(int(parameters["page_size"]), 100)
        
        url = f"{self.BASE_URL}/blocks/{block_id}/children"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        return {
            "success": True,
            "blocks": data.get("results", []),
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
            "total_count": len(data.get("results", []))
        }
    
    async def _append_blocks(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """添加内容块到页面"""
        block_id = parameters.get("block_id") or parameters.get("page_id")
        
        if not block_id:
            raise ValidationError("Missing required parameter: block_id or page_id")
        
        if "children" not in parameters:
            raise ValidationError("Missing required parameter: children")
        
        # 构建请求数据
        append_data = {
            "children": parameters["children"]
        }
        
        # 如果after参数存在，添加到请求中
        if "after" in parameters:
            append_data["after"] = parameters["after"]
        
        url = f"{self.BASE_URL}/blocks/{block_id}/children"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "PATCH", url, headers=headers, json_data=append_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        return {
            "success": True,
            "blocks": data.get("results", []),
            "message": f"Added {len(data.get('results', []))} blocks"
        }
    
    async def _update_block(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新块内容"""
        block_id = parameters.get("block_id")
        
        if not block_id:
            raise ValidationError("Missing required parameter: block_id")
        
        # 根据块类型构建更新数据
        block_type = parameters.get("type")
        if not block_type:
            raise ValidationError("Missing required parameter: type")
        
        update_data = {
            block_type: parameters.get(block_type, {})
        }
        
        # 如果提供了archived参数
        if "archived" in parameters:
            update_data["archived"] = parameters["archived"]
        
        url = f"{self.BASE_URL}/blocks/{block_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "PATCH", url, headers=headers, json_data=update_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        block = response.json()
        
        return {
            "success": True,
            "block": block,
            "block_id": block.get("id")
        }
    
    async def _delete_block(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除块"""
        block_id = parameters.get("block_id")
        
        if not block_id:
            raise ValidationError("Missing required parameter: block_id")
        
        url = f"{self.BASE_URL}/blocks/{block_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("DELETE", url, headers=headers)
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": "Block deleted successfully",
                "block_id": block_id
            }
        else:
            self._handle_http_error(response)
    
    async def _search(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """全局搜索"""
        # 构建搜索参数
        search_params = {}
        
        # 搜索查询
        if "query" in parameters:
            search_params["query"] = parameters["query"]
        
        # 过滤条件
        if "filter" in parameters:
            search_params["filter"] = parameters["filter"]
        
        # 排序
        if "sort" in parameters:
            search_params["sort"] = parameters["sort"]
        
        # 分页
        if "start_cursor" in parameters:
            search_params["start_cursor"] = parameters["start_cursor"]
        
        if "page_size" in parameters:
            search_params["page_size"] = min(int(parameters["page_size"]), 100)
        
        url = f"{self.BASE_URL}/search"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=search_params
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        return {
            "success": True,
            "results": data.get("results", []),
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
            "total_count": len(data.get("results", []))
        }
    
    async def _list_users(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出工作区用户"""
        # 构建查询参数
        query_params = {}
        
        if "start_cursor" in parameters:
            query_params["start_cursor"] = parameters["start_cursor"]
        
        if "page_size" in parameters:
            query_params["page_size"] = min(int(parameters["page_size"]), 100)
        
        url = f"{self.BASE_URL}/users"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        return {
            "success": True,
            "users": data.get("results", []),
            "has_more": data.get("has_more", False),
            "next_cursor": data.get("next_cursor"),
            "total_count": len(data.get("results", []))
        }
    
    async def _get_user(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取用户信息"""
        user_id = parameters.get("user_id")
        
        if not user_id:
            raise ValidationError("Missing required parameter: user_id")
        
        url = f"{self.BASE_URL}/users/{user_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        user = response.json()
        
        return {
            "success": True,
            "user": user
        }
    
    async def _default_connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Notion特定的连接测试"""
        # 尝试获取当前用户信息
        try:
            url = f"{self.BASE_URL}/users/me"
            headers = self._prepare_headers(credentials)
            
            response = await self.make_http_request("GET", url, headers=headers)
            
            if response.is_success:
                user_data = response.json()
                return {
                    "credentials_valid": True,
                    "workspace_access": True,
                    "user_type": user_data.get("type"),
                    "user_name": user_data.get("name"),
                    "user_id": user_data.get("id")
                }
            else:
                self._handle_http_error(response)
                
        except Exception as e:
            logger.warning(f"Notion connection test failed: {str(e)}")
            return {
                "credentials_valid": False,
                "error": str(e)
            }
    
    def _format_rich_text(self, text: Any) -> List[Dict[str, Any]]:
        """格式化文本为Notion的rich_text格式"""
        if isinstance(text, str):
            return [{"type": "text", "text": {"content": text}}]
        elif isinstance(text, list):
            # 已经是rich_text格式
            return text
        else:
            return [{"type": "text", "text": {"content": str(text)}}]
    
    def _handle_http_error(self, response):
        """处理Notion特定的HTTP错误响应
        
        覆盖父类方法以提供更详细的错误信息
        """
        try:
            error_data = response.json()
            error_code = error_data.get("code", "unknown")
            error_message = error_data.get("message", "Unknown error")
            
            # Notion特定的错误处理
            if response.status_code == 400:
                if error_code == "validation_error":
                    raise ValidationError(f"Notion validation error: {error_message}")
                else:
                    raise PermanentError(f"Bad request: {error_message}")
            elif response.status_code == 401:
                raise ValidationError(f"Authentication failed: {error_message}")
            elif response.status_code == 403:
                raise PermanentError(f"Insufficient permissions: {error_message}")
            elif response.status_code == 404:
                raise PermanentError(f"Resource not found: {error_message}")
            elif response.status_code == 429:
                # Rate limit错误
                retry_after = response.headers.get("retry-after")
                raise TemporaryError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            else:
                # 使用父类的默认处理
                super()._handle_http_error(response)
        except (json.JSONDecodeError, KeyError):
            # 如果无法解析错误响应，使用父类的默认处理
            super()._handle_http_error(response)