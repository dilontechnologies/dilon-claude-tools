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
} from '@modelcontextprotocol/sdk/types.js';

import { loadConfig, validateToolPaths } from './src/config.js';
import * as dilonCompiler from './src/tools/dilon-compiler.js';
import * as plantUML from './src/tools/plantuml.js';

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
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
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
        plantUML.toolDefinition
      ],
    };
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
  console.error('📦 Available tools: dilon_compile_doc, dilon_plantuml');
}

// Run the server
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
