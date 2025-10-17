#!/usr/bin/env node

/**
 * Post-install script for Dilon Claude Tools
 *
 * Automatically registers the MCP server with Claude Desktop
 * and performs dependency checks
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { homedir } from 'os';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageRoot = join(__dirname, '..');

console.log('');
console.log('========================================');
console.log('  Dilon Claude Tools Post-Install');
console.log('========================================');
console.log('');

// Get Claude Desktop config path
const claudeConfigPath = join(homedir(), 'AppData', 'Roaming', 'Claude', 'claude_desktop_config.json');
const serverPath = join(packageRoot, 'server.js');

/**
 * Register MCP server with Claude Desktop
 */
function registerMCPServer() {
  console.log('Step 1: Registering MCP server with Claude Desktop...');

  // Create directory if it doesn't exist
  const configDir = dirname(claudeConfigPath);
  if (!existsSync(configDir)) {
    mkdirSync(configDir, { recursive: true });
    console.log('  → Created Claude config directory');
  }

  // Load or create config
  let config = {};
  if (existsSync(claudeConfigPath)) {
    try {
      const configData = readFileSync(claudeConfigPath, 'utf8');
      config = JSON.parse(configData);
      console.log('  → Loaded existing Claude Desktop config');
    } catch (error) {
      console.log('  ⚠️  Could not parse existing config, creating new one');
      config = {};
    }
  } else {
    console.log('  → Creating new Claude Desktop config');
  }

  // Ensure mcpServers object exists
  if (!config.mcpServers) {
    config.mcpServers = {};
  }

  // Add/update dilon-claude-tools entry
  config.mcpServers['dilon-claude-tools'] = {
    command: 'node',
    args: [serverPath]
  };

  // Write config
  try {
    writeFileSync(claudeConfigPath, JSON.stringify(config, null, 2), 'utf8');
    console.log('  ✓ MCP server registered successfully');
    console.log(`  → Server path: ${serverPath}`);
  } catch (error) {
    console.error('  ❌ Failed to write config:', error.message);
    process.exit(1);
  }
}

/**
 * Create default config file
 */
function createDefaultConfig() {
  console.log('');
  console.log('Step 2: Creating default configuration...');

  const configPath = join(packageRoot, '.dilon-tools-config.json');
  const exampleConfigPath = join(packageRoot, '.dilon-tools-config.example.json');

  if (existsSync(configPath)) {
    console.log('  → Configuration file already exists');
    return;
  }

  // Load example config
  if (!existsSync(exampleConfigPath)) {
    console.log('  ⚠️  Example config not found, skipping');
    return;
  }

  try {
    const exampleConfig = readFileSync(exampleConfigPath, 'utf8');
    writeFileSync(configPath, exampleConfig, 'utf8');
    console.log('  ✓ Default configuration created');
    console.log(`  → Config path: ${configPath}`);
  } catch (error) {
    console.error('  ⚠️  Could not create config:', error.message);
  }
}

/**
 * Check for required dependencies
 */
function checkDependencies() {
  console.log('');
  console.log('Step 3: Checking dependencies...');

  const checks = [
    { name: 'Python', command: 'python --version' },
    { name: 'Pandoc', command: 'pandoc --version' },
    { name: 'Java', command: 'java -version' }
  ];

  let missingDeps = [];

  checks.forEach(({ name, command }) => {
    try {
      execSync(command, { stdio: 'ignore' });
      console.log(`  ✓ ${name} found`);
    } catch (error) {
      console.log(`  ✗ ${name} not found`);
      missingDeps.push(name);
    }
  });

  if (missingDeps.length > 0) {
    console.log('');
    console.log('  ⚠️  Missing dependencies detected:');
    missingDeps.forEach(dep => console.log(`     - ${dep}`));
    console.log('');
    console.log('  To install missing dependencies, run:');
    console.log('    npm explore @dilon/claude-tools -- npm run install-deps');
    console.log('  Or install manually from:');
    console.log('    Python:  https://www.python.org/downloads/');
    console.log('    Pandoc:  https://pandoc.org/installing.html');
    console.log('    Java:    https://adoptium.net/');
  }
}

/**
 * Show completion message
 */
function showCompletion() {
  console.log('');
  console.log('========================================');
  console.log('  ✓ Installation Complete!');
  console.log('========================================');
  console.log('');
  console.log('Next steps:');
  console.log('  1. Restart Claude Desktop to load the MCP server');
  console.log('  2. The following tools will be available:');
  console.log('     • dilon_compile_doc - Compile Markdown to Word');
  console.log('     • dilon_plantuml - Generate diagrams');
  console.log('');
  console.log('CLI commands:');
  console.log('  dilon-tools info    - Show package information');
  console.log('  dilon-tools help    - Show all available commands');
  console.log('');
  console.log('Documentation:');
  console.log(`  ${join(packageRoot, 'README.md')}`);
  console.log('');
}

// Run installation steps
try {
  registerMCPServer();
  createDefaultConfig();
  checkDependencies();
  showCompletion();
} catch (error) {
  console.error('');
  console.error('❌ Post-install failed:', error.message);
  console.error('');
  process.exit(1);
}
