/// <reference types="vite/client" />

/**
 * Vite environment variables type declarations.
 * All VITE_ prefixed environment variables must be declared here
 * to benefit from TypeScript autocompletion and type safety.
 */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
