/**
 * Configuration Manager for Dilon Claude Tools MCP Server
 *
 * Loads and validates configuration from .dilon-tools-config.json
 * Provides paths to embedded tools and external dependencies
 */

import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = join(__dirname, '..');

/**
 * Load configuration from .dilon-tools-config.json
 * Falls back to example config if user config doesn't exist
 *
 * @returns {Object} Configuration object
 * @throws {Error} If configuration file is invalid or missing required fields
 */
export function loadConfig() {
  const configPath = join(PROJECT_ROOT, '.dilon-tools-config.json');
  const exampleConfigPath = join(PROJECT_ROOT, '.dilon-tools-config.example.json');

  let configFile = configPath;

  // Check if user config exists, otherwise use example
  if (!existsSync(configPath)) {
    console.warn('⚠️  User configuration not found at:', configPath);
    console.warn('📋 Using example configuration. Please run install.ps1 to create your config.');

    if (!existsSync(exampleConfigPath)) {
      throw new Error('Neither .dilon-tools-config.json nor .dilon-tools-config.example.json found');
    }

    configFile = exampleConfigPath;
  }

  try {
    const configData = readFileSync(configFile, 'utf8');
    const config = JSON.parse(configData);

    // Validate required fields
    const requiredFields = ['pythonPath', 'plantUmlPath', 'pandocPath'];
    const missingFields = requiredFields.filter(field => !config[field]);

    if (missingFields.length > 0) {
      throw new Error(`Missing required configuration fields: ${missingFields.join(', ')}`);
    }

    return config;
  } catch (error) {
    throw new Error(`Failed to load configuration from ${configFile}: ${error.message}`);
  }
}

/**
 * Get paths to Dilon Document Compiler components (embedded in this repo)
 *
 * @returns {Object} Paths to compiler script and templates
 */
export function getDilonCompilerPaths() {
  const compilerDir = join(PROJECT_ROOT, 'tools', 'Dilon_Document_Compiler');

  return {
    scriptPath: join(compilerDir, 'generate_dilon_doc.py'),
    signatureTemplate: join(compilerDir, 'TEMPLATE_Word_Signature.docx'),
    contentTemplate: join(compilerDir, 'TEMPLATE_Word_Content.docx'),
    documentTemplate: join(PROJECT_ROOT, 'docs', 'TEMPLATE_Document.md'),
    stylingGuide: join(PROJECT_ROOT, 'docs', 'MARKDOWN_STYLING_GUIDE.md')
  };
}

/**
 * Get path to PlantUML style guide (embedded in this repo)
 *
 * @returns {string} Path to PlantUML style guide
 */
export function getPlantUMLStyleGuide() {
  return join(PROJECT_ROOT, 'docs', 'PlantUML_Style_Guide.md');
}

/**
 * Get paths to all documentation/style guides
 *
 * @returns {Object} Paths to documentation files
 */
export function getDocumentationPaths() {
  return {
    markdownStyling: join(PROJECT_ROOT, 'docs', 'MARKDOWN_STYLING_GUIDE.md'),
    plantUmlStyling: join(PROJECT_ROOT, 'docs', 'PlantUML_Style_Guide.md')
  };
}

/**
 * Validate that all required external tools and embedded tools are accessible
 *
 * @param {Object} config - Configuration object from loadConfig()
 * @returns {Object} Validation results with details for each tool
 */
export function validateToolPaths(config) {
  const results = {
    valid: true,
    errors: [],
    warnings: []
  };

  // Check embedded Dilon Compiler exists
  const compilerPaths = getDilonCompilerPaths();
  if (!existsSync(compilerPaths.scriptPath)) {
    results.valid = false;
    results.errors.push(`Dilon Compiler script not found at: ${compilerPaths.scriptPath}`);
  }

  // Check templates exist
  if (!existsSync(compilerPaths.signatureTemplate)) {
    results.warnings.push(`Signature template not found: ${compilerPaths.signatureTemplate}`);
  }
  if (!existsSync(compilerPaths.contentTemplate)) {
    results.warnings.push(`Content template not found: ${compilerPaths.contentTemplate}`);
  }

  // Check styling guides exist
  const docPaths = getDocumentationPaths();
  if (!existsSync(docPaths.markdownStyling)) {
    results.warnings.push(`Markdown styling guide not found: ${docPaths.markdownStyling}`);
  }
  if (!existsSync(docPaths.plantUmlStyling)) {
    results.warnings.push(`PlantUML styling guide not found: ${docPaths.plantUmlStyling}`);
  }

  // Check external PlantUML directory exists
  if (!existsSync(config.plantUmlPath)) {
    results.warnings.push(`PlantUML directory not found at: ${config.plantUmlPath}`);
  }

  return results;
}
