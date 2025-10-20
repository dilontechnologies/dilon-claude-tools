#!/usr/bin/env node

/**
 * Dilon Claude Tools MCP Server
 *
 * Model Context Protocol server providing Dilon Diagnostics tools
 * for Claude Code integration
 *
 * Tools:
 * - dilon_compile_doc: Compile Markdown to formatted Word documents
 * - dilon_plantuml: Generate diagrams from PlantUML files
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { loadConfig, validateToolPaths } from './src/config.js';
import * as dilonCompiler from './src/tools/dilon-compiler.js';
import * as plantUML from './src/tools/plantuml.js';
import * as generateStub from './src/tools/generate-stub.js';

// Get package root directory for resource paths
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PACKAGE_ROOT = resolve(__dirname);

/**
 * Initialize and start the MCP server
 */
async function main() {
  // Load configuration
  let config;
  try {
    config = loadConfig();
    console.error('✅ Configuration loaded');

    // Validate tool paths
    const validation = validateToolPaths(config);
    if (!validation.valid) {
      console.error('❌ Configuration validation failed:');
      validation.errors.forEach(err => console.error(`  - ${err}`));
      process.exit(1);
    }

    if (validation.warnings.length > 0) {
      console.error('⚠️  Configuration warnings:');
      validation.warnings.forEach(warn => console.error(`  - ${warn}`));
    }
  } catch (error) {
    console.error('❌ Failed to load configuration:', error.message);
    console.error('\nPlease run install.ps1 to configure the MCP server.');
    process.exit(1);
  }

  // Create MCP server instance
  const server = new Server(
    {
      name: 'dilon-claude-tools',
      version: '1.1.0',
    },
    {
      capabilities: {
        tools: {},
        resources: {},
      },
    }
  );

  /**
   * Handler for listing available tools
   */
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        dilonCompiler.toolDefinition,
        plantUML.toolDefinition,
        generateStub.toolDefinition
      ],
    };
  });

  /**
   * Handler for listing available resources
   */
  server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return {
      resources: [
        {
          uri: 'dilon://styling/markdown',
          name: 'Markdown Styling Guide',
          description: 'Comprehensive Dilon markdown styling guide covering YAML front matter, ' +
                       'heading conventions, tables, figures, lists, code blocks, custom styles, ' +
                       'and regulatory compliance formatting for Word document generation.',
          mimeType: 'text/markdown'
        },
        {
          uri: 'dilon://styling/plantuml',
          name: 'PlantUML Style Guide',
          description: 'Dilon PlantUML style guide covering xUML/Executable UML conventions, ' +
                       'class diagrams, state machines, domain diagrams, naming conventions, ' +
                       'relationship notation, and identifier formatting.',
          mimeType: 'text/markdown'
        }
      ],
    };
  });

  /**
   * Handler for reading resource content
   */
  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const { uri } = request.params;

    try {
      let filePath;

      switch (uri) {
        case 'dilon://styling/markdown':
          filePath = resolve(PACKAGE_ROOT, 'docs', 'MARKDOWN_STYLING_GUIDE.md');
          break;

        case 'dilon://styling/plantuml':
          filePath = resolve(PACKAGE_ROOT, 'docs', 'PlantUML_Style_Guide.md');
          break;

        default:
          return {
            contents: [
              {
                uri,
                mimeType: 'text/plain',
                text: `Unknown resource URI: ${uri}`
              }
            ]
          };
      }

      // Read the resource file
      const content = readFileSync(filePath, 'utf-8');

      return {
        contents: [
          {
            uri,
            mimeType: 'text/markdown',
            text: content
          }
        ]
      };

    } catch (error) {
      return {
        contents: [
          {
            uri,
            mimeType: 'text/plain',
            text: `Error reading resource ${uri}: ${error.message}`
          }
        ]
      };
    }
  });

  /**
   * Handler for tool execution
   */
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case 'dilon_compile_doc':
          return await dilonCompiler.execute(args, config);

        case 'dilon_plantuml':
          return await plantUML.execute(args, config);

        case 'dilon_generate_stub':
          return await generateStub.execute(args, config);

        default:
          return {
            content: [
              {
                type: 'text',
                text: `Unknown tool: ${name}`,
              },
            ],
            isError: true,
          };
      }
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Error executing tool ${name}: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  });

  // Start the server using stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('🚀 Dilon Claude Tools MCP Server started');
  console.error('📦 Available tools: dilon_compile_doc, dilon_plantuml, dilon_generate_stub');
  console.error('📚 Available resources: dilon://styling/markdown, dilon://styling/plantuml');
}

// Run the server
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
