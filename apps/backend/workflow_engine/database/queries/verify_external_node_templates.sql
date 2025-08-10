-- ============================================================================
-- 验证外部API集成节点模板
-- 确认node_templates表中的数据与node_specs规范一致
-- ============================================================================

-- 1. 查看所有EXTERNAL_ACTION_NODE类型的模板
SELECT 
    template_id,
    name,
    description,
    category,
    node_subtype,
    jsonb_array_length(
        CASE 
            WHEN jsonb_typeof(default_parameters) = 'object' 
            THEN jsonb_object_keys(default_parameters) 
            ELSE '[]'::jsonb 
        END
    ) as default_params_count,
    array_length(required_parameters, 1) as required_params_count,
    is_system_template,
    created_at
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE'
ORDER BY node_subtype;

-- 2. 详细查看Google Calendar模板
SELECT 
    '=== GOOGLE_CALENDAR 模板详情 ===' as info;

SELECT 
    template_id,
    name,
    description,
    jsonb_pretty(default_parameters) as default_parameters,
    required_parameters,
    jsonb_pretty(parameter_schema) as parameter_schema
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE' 
AND node_subtype = 'GOOGLE_CALENDAR';

-- 3. 检查所有外部节点的必需参数
SELECT 
    '=== 所有外部节点的必需参数 ===' as info;

SELECT 
    node_subtype,
    name,
    required_parameters,
    array_length(required_parameters, 1) as param_count
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE'
ORDER BY node_subtype;

-- 4. 检查参数schema的完整性
SELECT 
    '=== 参数Schema验证 ===' as info;

SELECT 
    node_subtype,
    name,
    CASE 
        WHEN parameter_schema ? 'properties' THEN '✅ 有properties'
        ELSE '❌ 缺少properties'
    END as has_properties,
    CASE 
        WHEN parameter_schema ? 'required' THEN '✅ 有required'
        ELSE '❌ 缺少required'
    END as has_required,
    CASE 
        WHEN parameter_schema->>'type' = 'object' THEN '✅ 类型正确'
        ELSE '❌ 类型错误: ' || (parameter_schema->>'type')
    END as type_check,
    jsonb_object_keys(parameter_schema->'properties') as property_keys
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE'
ORDER BY node_subtype;

-- 5. 统计信息
SELECT 
    '=== 统计信息 ===' as info;

SELECT 
    'EXTERNAL_ACTION_NODE 模板总数' as metric,
    count(*) as value
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE';

SELECT 
    '系统模板数量' as metric,
    count(*) as value
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE' 
AND is_system_template = true;

SELECT 
    '用户自定义模板数量' as metric,
    count(*) as value
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE' 
AND is_system_template = false;

-- 6. 验证模板ID的唯一性
SELECT 
    '=== 模板ID唯一性检查 ===' as info;

SELECT 
    template_id,
    count(*) as duplicate_count
FROM public.node_templates 
WHERE node_type = 'EXTERNAL_ACTION_NODE'
GROUP BY template_id
HAVING count(*) > 1;

-- 如果上面的查询没有返回结果，说明所有template_id都是唯一的