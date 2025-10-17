#!/usr/bin/env node

/**
 * Dilon Claude Tools CLI
 *
 * Global command for managing the Dilon Claude Tools MCP server
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageRoot = join(__dirname, '..');

// Load package.json for version info
const packageJson = JSON.parse(
  readFileSync(join(packageRoot, 'package.json'), 'utf8')
);

const commands = {
  version: () => {
    console.log(`Dilon Claude Tools v${packageJson.version}`);
  },

  info: () => {
    console.log('Dilon Claude Tools MCP Server');
    console.log('');
    console.log(`Version:     ${packageJson.version}`);
    console.log(`Install Dir: ${packageRoot}`);
    console.log(`Author:      ${packageJson.author}`);
    console.log('');
    console.log('Tools available:');
    console.log('  • dilon_compile_doc - Compile Markdown to Word documents');
    console.log('  • dilon_plantuml    - Generate diagrams from PlantUML files');
    console.log('');
    console.log('For usage instructions, see:');
    console.log(`  ${join(packageRoot, 'README.md')}`);
  },

  path: () => {
    console.log(packageRoot);
  },

  'server-path': () => {
    console.log(join(packageRoot, 'server.js'));
  },

  config: () => {
    const configPath = join(packageRoot, '.dilon-tools-config.json');
    const examplePath = join(packageRoot, '.dilon-tools-config.example.json');

    console.log('Configuration file locations:');
    console.log(`  Config:  ${configPath}`);
    console.log(`  Example: ${examplePath}`);
  },

  help: () => {
    console.log('Dilon Claude Tools CLI');
    console.log('');
    console.log('Usage: dilon-tools <command>');
    console.log('');
    console.log('Commands:');
    console.log('  version       Show version number');
    console.log('  info          Show package information and available tools');
    console.log('  path          Show installation directory');
    console.log('  server-path   Show path to MCP server.js');
    console.log('  config        Show configuration file paths');
    console.log('  help          Show this help message');
    console.log('');
    console.log('The MCP server is automatically registered with Claude Desktop');
    console.log('during installation. No manual configuration needed.');
    console.log('');
    console.log('Documentation:');
    console.log(`  ${join(packageRoot, 'README.md')}`);
  }
};

// Parse command
const command = process.argv[2] || 'help';

if (commands[command]) {
  commands[command]();
} else {
  console.error(`Unknown command: ${command}`);
  console.error('Run "dilon-tools help" for usage information');
  process.exit(1);
}
