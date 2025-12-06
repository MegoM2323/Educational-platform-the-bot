import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import react from "eslint-plugin-react";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react": react,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": "off",
      // Enforce explicit type attribute on native <button> elements
      // NOTE: This rule only catches native HTML <button> elements, NOT custom <Button> components
      // For custom Button components, manually ensure all have type="button" or type="submit"
      // - type="button" for non-submit actions (default)
      // - type="submit" for form submissions only
      // This prevents implicit form submission when buttons are inside <form> elements
      "react/button-has-type": ["error", {
        "button": true,
        "submit": true,
        "reset": true
      }],
    },
  },
);
