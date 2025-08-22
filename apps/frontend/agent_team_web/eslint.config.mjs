import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  // Global ignores must be in a separate object
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/out/**",
      "**/build/**",
      "src/app/(dev)/**",  // Ignore all test pages in dev folder
      "src/app/**/*-test/**",  // Ignore any test folders
    ],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",  // 警告而非错误，允许在必要时使用
      "@typescript-eslint/no-unused-vars": ["error", { 
        "argsIgnorePattern": "^_",  // 允许 _开头的未使用变量
        "varsIgnorePattern": "^_"
      }],
      "@next/next/no-img-element": "warn",  // 保留警告，提醒性能优化
      "react-hooks/exhaustive-deps": "warn",  // 保留警告，避免潜在bug
      "jsx-a11y/alt-text": "warn",  // 保留警告，保持可访问性
    },
  },
];

export default eslintConfig;
