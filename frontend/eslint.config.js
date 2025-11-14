// eslint.config.js (ESLint 9+ flat config)
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactPlugin from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default [
  {
    files: ["src/**/*.{ts,tsx}", "vite-env.d.ts"], // Source files and type definitions
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: ["./tsconfig.app.json"], // Array with the app config that includes src/
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      react: reactPlugin,
      "react-hooks": reactHooks,
    },
    rules: {
      // TypeScript rules
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "off",

      // React rules
      "react/react-in-jsx-scope": "off", // Not needed with React 17+
      "react/prop-types": "off",

      // React Hooks
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  {
    files: ["vite.config.ts"], // Build/config files
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: ["./tsconfig.node.json"], // Node config for build files
      },
      globals: {
        ...globals.node,
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
    },
    rules: {
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
];
