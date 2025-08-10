import React from 'react';
import ComponentCreator from '@docusaurus/ComponentCreator';

export default [
  {
    path: '/blog',
    component: ComponentCreator('/blog', 'b2f'),
    exact: true
  },
  {
    path: '/blog/archive',
    component: ComponentCreator('/blog/archive', '182'),
    exact: true
  },
  {
    path: '/blog/authors',
    component: ComponentCreator('/blog/authors', '0b7'),
    exact: true
  },
  {
    path: '/blog/authors/all-sebastien-lorber-articles',
    component: ComponentCreator('/blog/authors/all-sebastien-lorber-articles', '4a1'),
    exact: true
  },
  {
    path: '/blog/authors/yangshun',
    component: ComponentCreator('/blog/authors/yangshun', 'a68'),
    exact: true
  },
  {
    path: '/blog/first-blog-post',
    component: ComponentCreator('/blog/first-blog-post', '89a'),
    exact: true
  },
  {
    path: '/blog/long-blog-post',
    component: ComponentCreator('/blog/long-blog-post', '9ad'),
    exact: true
  },
  {
    path: '/blog/mdx-blog-post',
    component: ComponentCreator('/blog/mdx-blog-post', 'e9f'),
    exact: true
  },
  {
    path: '/blog/tags',
    component: ComponentCreator('/blog/tags', '287'),
    exact: true
  },
  {
    path: '/blog/tags/docusaurus',
    component: ComponentCreator('/blog/tags/docusaurus', '704'),
    exact: true
  },
  {
    path: '/blog/tags/facebook',
    component: ComponentCreator('/blog/tags/facebook', '858'),
    exact: true
  },
  {
    path: '/blog/tags/hello',
    component: ComponentCreator('/blog/tags/hello', '299'),
    exact: true
  },
  {
    path: '/blog/tags/hola',
    component: ComponentCreator('/blog/tags/hola', '00d'),
    exact: true
  },
  {
    path: '/blog/welcome',
    component: ComponentCreator('/blog/welcome', 'd2b'),
    exact: true
  },
  {
    path: '/markdown-page',
    component: ComponentCreator('/markdown-page', '3d7'),
    exact: true
  },
  {
    path: '/docs',
    component: ComponentCreator('/docs', '6b2'),
    routes: [
      {
        path: '/docs',
        component: ComponentCreator('/docs', '844'),
        routes: [
          {
            path: '/docs',
            component: ComponentCreator('/docs', '280'),
            routes: [
              {
                path: '/docs/',
                component: ComponentCreator('/docs/', '441'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/development/',
                component: ComponentCreator('/docs/development/', '3dd'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/development/agent_development_one_pager',
                component: ComponentCreator('/docs/development/agent_development_one_pager', '36a'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/development/api_workflow_integration',
                component: ComponentCreator('/docs/development/api_workflow_integration', 'f43'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/development/DEPLOYMENT',
                component: ComponentCreator('/docs/development/DEPLOYMENT', 'b8a'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/development/NODE_SPEC_IMPLEMENTATION_PLAN',
                component: ComponentCreator('/docs/development/NODE_SPEC_IMPLEMENTATION_PLAN', 'd71'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/development/workflow_agent_mvp_plan',
                component: ComponentCreator('/docs/development/workflow_agent_mvp_plan', 'a82'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/development/workflow_runtime_tasks',
                component: ComponentCreator('/docs/development/workflow_runtime_tasks', '0b4'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/product-design/',
                component: ComponentCreator('/docs/product-design/', '298'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/product-design/core-product-design',
                component: ComponentCreator('/docs/product-design/core-product-design', '12d'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/',
                component: ComponentCreator('/docs/tech-design/', 'ab5'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/api-gateway-architecture',
                component: ComponentCreator('/docs/tech-design/api-gateway-architecture', 'eb2'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/data_mapping_system',
                component: ComponentCreator('/docs/tech-design/data_mapping_system', 'd89'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/db-design',
                component: ComponentCreator('/docs/tech-design/db-design', '8b7'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/distributed-tracing-system',
                component: ComponentCreator('/docs/tech-design/distributed-tracing-system', 'c1b'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/grpc-to-fastapi-migration',
                component: ComponentCreator('/docs/tech-design/grpc-to-fastapi-migration', '6ad'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/grpc-to-fastapi-migration-zh',
                component: ComponentCreator('/docs/tech-design/grpc-to-fastapi-migration-zh', '742'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/mcp-node-knowledge-server',
                component: ComponentCreator('/docs/tech-design/mcp-node-knowledge-server', '468'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/mvp-workflow-data-structure-definition',
                component: ComponentCreator('/docs/tech-design/mvp-workflow-data-structure-definition', '3d4'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/mvp-workflow-planning',
                component: ComponentCreator('/docs/tech-design/mvp-workflow-planning', 'ec0'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/node_spec',
                component: ComponentCreator('/docs/tech-design/node_spec', '126'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/node-structure',
                component: ComponentCreator('/docs/tech-design/node-structure', '4a2'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/workflow-agent-api-doc',
                component: ComponentCreator('/docs/tech-design/workflow-agent-api-doc', '817'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/workflow-agent-architecture',
                component: ComponentCreator('/docs/tech-design/workflow-agent-architecture', '7dc'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/workflow-engine-architecure',
                component: ComponentCreator('/docs/tech-design/workflow-engine-architecure', '924'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/tech-design/workflow-runtime-architecture',
                component: ComponentCreator('/docs/tech-design/workflow-runtime-architecture', 'c53'),
                exact: true,
                sidebar: "tutorialSidebar"
              }
            ]
          }
        ]
      }
    ]
  },
  {
    path: '/',
    component: ComponentCreator('/', 'e5f'),
    exact: true
  },
  {
    path: '*',
    component: ComponentCreator('*'),
  },
];
