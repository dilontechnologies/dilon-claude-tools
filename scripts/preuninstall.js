#!/usr/bin/env node

/**
 * Pre-uninstall script for Dilon Claude Tools
 *
 * Removes the MCP server registration from Claude Desktop config
 */

import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

console.log('');
console.log('Removing Dilon Claude Tools from Claude Desktop...');
console.log('');

const claudeConfigPath = join(homedir(), 'AppData', 'Roaming', 'Claude', 'claude_desktop_config.json');

if (!existsSync(claudeConfigPath)) {
  console.log('  ℹ️  No Claude Desktop config found, nothing to remove');
  process.exit(0);
}

try {
  // Load config
  const configData = readFileSync(claudeConfigPath, 'utf8');
  const config = JSON.parse(configData);

  // Remove dilon-claude-tools entry
  if (config.mcpServers && config.mcpServers['dilon-claude-tools']) {
    delete config.mcpServers['dilon-claude-tools'];

    // Write updated config
    writeFileSync(claudeConfigPath, JSON.stringify(config, null, 2), 'utf8');
    console.log('  ✓ MCP server unregistered from Claude Desktop');
  } else {
    console.log('  ℹ️  MCP server was not registered');
  }
} catch (error) {
  console.error('  ⚠️  Could not update Claude Desktop config:', error.message);
  console.error('  → You may need to manually remove "dilon-claude-tools" from:');
  console.error(`     ${claudeConfigPath}`);
}

console.log('');
console.log('  Note: Restart Claude Desktop to complete uninstallation');
console.log('');
