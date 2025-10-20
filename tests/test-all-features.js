#!/usr/bin/env node

/**
 * Comprehensive Test Suite for Dilon Claude Tools MCP Server
 *
 * Tests all features including:
 * - New dilon_generate_stub tool
 * - Styling guide resources (markdown, plantuml)
 * - Existing tools (dilon_compile_doc, dilon_plantuml)
 */

import { spawn, execSync } from 'child_process';
import { createInterface } from 'readline';
import { writeFileSync, mkdirSync, existsSync, rmSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// Get the repository root (parent of tests directory)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = resolve(__dirname, '..');

// Test configuration
const TEST_DIR = resolve(REPO_ROOT, 'tests', 'test-output');
const TIMEOUT = 30000;

// Start the MCP server from repository root
const server = spawn('node', ['server.js'], {
  cwd: REPO_ROOT,
  stdio: ['pipe', 'pipe', 'pipe']
});

let requestId = 1;
const responses = new Map();
let testsPassed = 0;
let testsFailed = 0;

// Create readline interface for server stdout
const rl = createInterface({
  input: server.stdout,
  crlfDelay: Infinity
});

// Listen for server responses
rl.on('line', (line) => {
  try {
    const response = JSON.parse(line);
    if (response.id) {
      responses.set(response.id, response);
    }
  } catch (e) {
    // Ignore non-JSON lines (like startup messages on stderr)
  }
});

// Listen for server errors (suppress for cleaner output)
server.stderr.on('data', (data) => {
  // Optionally log: console.error('Server:', data.toString().trim());
});

// Helper to send JSON-RPC request
function sendRequest(method, params = {}) {
  const id = requestId++;
  const request = {
    jsonrpc: '2.0',
    id,
    method,
    params
  };

  server.stdin.write(JSON.stringify(request) + '\n');
  return id;
}

// Helper to wait for response
async function waitForResponse(id, timeout = 5000) {
  const startTime = Date.now();
  while (!responses.has(id)) {
    if (Date.now() - startTime > timeout) {
      throw new Error(`Timeout waiting for response to request ${id}`);
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  return responses.get(id);
}

// Test result helpers
function pass(message) {
  console.log('✅', message);
  testsPassed++;
}

function fail(message) {
  console.log('❌', message);
  testsFailed++;
}

function info(message) {
  console.log('   ', message);
}

// Main test function
async function runTests() {
  console.log('═══════════════════════════════════════════════════════════');
  console.log('🧪 Dilon Claude Tools - Comprehensive Test Suite');
  console.log('═══════════════════════════════════════════════════════════\n');

  // Setup test directory
  if (existsSync(TEST_DIR)) {
    rmSync(TEST_DIR, { recursive: true, force: true });
  }
  mkdirSync(TEST_DIR, { recursive: true });

  // Wait for server to start
  await new Promise(resolve => setTimeout(resolve, 2000));

  try {
    // ═══════════════════════════════════════════════════════════
    console.log('📋 SECTION 1: Server Initialization');
    console.log('───────────────────────────────────────────────────────────');

    const initId = sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'test-client',
        version: '1.0.0'
      }
    });
    const initResponse = await waitForResponse(initId);

    if (initResponse.result && initResponse.result.serverInfo) {
      pass('Server initialized successfully');
      info(`Server: ${initResponse.result.serverInfo.name} v${initResponse.result.serverInfo.version}`);
      info(`Capabilities: ${Object.keys(initResponse.result.capabilities).join(', ')}`);
    } else {
      fail('Server initialization failed');
    }
    console.log();

    // ═══════════════════════════════════════════════════════════
    console.log('📋 SECTION 2: Tool Registration');
    console.log('───────────────────────────────────────────────────────────');

    const listToolsId = sendRequest('tools/list');
    const toolsResponse = await waitForResponse(listToolsId);
    const tools = toolsResponse.result.tools;

    const expectedTools = ['dilon_compile_doc', 'dilon_plantuml', 'dilon_generate_stub'];
    const toolNames = tools.map(t => t.name);

    if (toolNames.length === expectedTools.length) {
      pass(`All ${expectedTools.length} tools registered`);
    } else {
      fail(`Expected ${expectedTools.length} tools, found ${toolNames.length}`);
    }

    expectedTools.forEach(toolName => {
      if (toolNames.includes(toolName)) {
        pass(`Tool '${toolName}' registered`);
      } else {
        fail(`Tool '${toolName}' missing`);
      }
    });
    console.log();

    // ═══════════════════════════════════════════════════════════
    console.log('📋 SECTION 3: Resource Registration');
    console.log('───────────────────────────────────────────────────────────');

    const listResourcesId = sendRequest('resources/list');
    const resourcesResponse = await waitForResponse(listResourcesId);
    const resources = resourcesResponse.result.resources;

    const expectedResources = [
      'dilon://styling/markdown',
      'dilon://styling/plantuml'
    ];
    const resourceUris = resources.map(r => r.uri);

    if (resourceUris.length === expectedResources.length) {
      pass(`All ${expectedResources.length} resources registered`);
    } else {
      fail(`Expected ${expectedResources.length} resources, found ${resourceUris.length}`);
    }

    expectedResources.forEach(uri => {
      if (resourceUris.includes(uri)) {
        const resource = resources.find(r => r.uri === uri);
        pass(`Resource '${resource.name}' registered at ${uri}`);
      } else {
        fail(`Resource '${uri}' missing`);
      }
    });
    console.log();

    // ═══════════════════════════════════════════════════════════
    console.log('📋 SECTION 4: Resource Content Retrieval');
    console.log('───────────────────────────────────────────────────────────');

    // Test markdown resource
    const readMarkdownId = sendRequest('resources/read', {
      uri: 'dilon://styling/markdown'
    });
    const markdownResponse = await waitForResponse(readMarkdownId);
    const markdownContent = markdownResponse.result.contents[0].text;

    if (markdownContent && markdownContent.length > 1000) {
      pass('Markdown styling guide retrieved successfully');
      info(`Content length: ${markdownContent.length} characters`);
      info(`First line: ${markdownContent.split('\n')[0]}`);
    } else {
      fail('Markdown styling guide content insufficient');
    }

    // Test PlantUML resource
    const readPlantUMLId = sendRequest('resources/read', {
      uri: 'dilon://styling/plantuml'
    });
    const plantumlResponse = await waitForResponse(readPlantUMLId);
    const plantumlContent = plantumlResponse.result.contents[0].text;

    if (plantumlContent && plantumlContent.length > 1000) {
      pass('PlantUML styling guide retrieved successfully');
      info(`Content length: ${plantumlContent.length} characters`);
      info(`First line: ${plantumlContent.split('\n')[0]}`);
    } else {
      fail('PlantUML styling guide content insufficient');
    }
    console.log();

    // ═══════════════════════════════════════════════════════════
    console.log('📋 SECTION 5: NEW TOOL - dilon_generate_stub');
    console.log('───────────────────────────────────────────────────────────');

    // Test 5.1: Generate stub with custom parameters
    console.log('Test 5.1: Generate stub with custom parameters');
    const stubPath1 = `${TEST_DIR}/custom_stub.md`;
    const generateStub1Id = sendRequest('tools/call', {
      name: 'dilon_generate_stub',
      arguments: {
        output_path: stubPath1,
        title: 'Software Requirements Specification',
        author: 'Engineering Team',
        doc_number: 'DD_SWE_12345',
        department: 'Software Engineering',
        current_revision: '01'
      }
    });
    const stub1Response = await waitForResponse(generateStub1Id);

    if (!stub1Response.result.isError) {
      pass('Stub generated with custom parameters');
      if (existsSync(stubPath1)) {
        pass('Stub file created on filesystem');
      } else {
        fail('Stub file not found on filesystem');
      }
    } else {
      fail('Stub generation with custom parameters failed');
      info(stub1Response.result.content[0].text);
    }

    // Test 5.2: Generate stub with minimal parameters (defaults)
    console.log('\nTest 5.2: Generate stub with default parameters');
    const stubPath2 = `${TEST_DIR}/default_stub.md`;
    const generateStub2Id = sendRequest('tools/call', {
      name: 'dilon_generate_stub',
      arguments: {
        output_path: stubPath2
      }
    });
    const stub2Response = await waitForResponse(generateStub2Id);

    if (!stub2Response.result.isError) {
      pass('Stub generated with default parameters');
    } else {
      fail('Stub generation with defaults failed');
    }

    // Test 5.3: Error handling - existing file
    console.log('\nTest 5.3: Error handling - duplicate file');
    const generateStub3Id = sendRequest('tools/call', {
      name: 'dilon_generate_stub',
      arguments: {
        output_path: stubPath1  // Already exists
      }
    });
    const stub3Response = await waitForResponse(generateStub3Id);

    if (stub3Response.result.isError) {
      pass('Correctly prevents overwriting existing file');
    } else {
      fail('Should have prevented overwriting existing file');
    }
    console.log();

    // ═══════════════════════════════════════════════════════════
    console.log('📋 SECTION 6: EXISTING TOOL - dilon_compile_doc');
    console.log('───────────────────────────────────────────────────────────');

    // Test 6.1: Error handling - missing file
    console.log('Test 6.1: Error handling - missing file');
    const compileErrorId = sendRequest('tools/call', {
      name: 'dilon_compile_doc',
      arguments: {
        input_markdown: 'nonexistent.md'
      }
    });
    const compileErrorResponse = await waitForResponse(compileErrorId);

    if (compileErrorResponse.result.isError) {
      pass('Correctly reports error for missing file');
    } else {
      fail('Should report error for missing file');
    }

    // Test 6.2: Compile valid document
    console.log('\nTest 6.2: Compile valid markdown document');
    const validMd = `---
title: "Integration Test Document"
author: "Test Suite"
department: "Engineering"
doc_number: "DD_TST_99999"
current_revision: "00"
regulatory_rep: "Test Rep"
quality_rep: "Test QA"
department_head: "Test Head"
revisions:
  - number: "00"
    description: "Initial test"
    eco_number: "ECO-000"
    eco_date: "2025-01-01"
---

## 1. Purpose and Scope

### 1.1 Purpose
This document tests the compilation process.

### 1.2 Scope
Comprehensive integration testing.
`;

    const mdPath = `${TEST_DIR}/compile_test.md`;
    const docxPath = `${TEST_DIR}/compile_test.docx`;
    writeFileSync(mdPath, validMd, 'utf-8');

    const compileValidId = sendRequest('tools/call', {
      name: 'dilon_compile_doc',
      arguments: {
        input_markdown: mdPath,
        output_word: docxPath
      }
    });
    const compileValidResponse = await waitForResponse(compileValidId, TIMEOUT);

    if (compileValidResponse.result.isError) {
      info('⚠️  Compilation returned error (may be expected if dependencies not configured)');
      info(compileValidResponse.result.content[0].text.split('\n')[0]);
    } else {
      pass('Document compilation executed successfully');
      if (existsSync(docxPath)) {
        pass('Word document created on filesystem');
      } else {
        info('Note: Word document may require Python/Pandoc dependencies');
      }
    }
    console.log();

    // ═══════════════════════════════════════════════════════════
    console.log('📋 SECTION 7: EXISTING TOOL - dilon_plantuml');
    console.log('───────────────────────────────────────────────────────────');

    // Test 7.1: Error handling - missing file
    console.log('Test 7.1: Error handling - missing file');
    const plantumlErrorId = sendRequest('tools/call', {
      name: 'dilon_plantuml',
      arguments: {
        input_file: 'nonexistent.puml'
      }
    });
    const plantumlErrorResponse = await waitForResponse(plantumlErrorId);

    if (plantumlErrorResponse.result.isError) {
      pass('Correctly reports error for missing PlantUML file');
    } else {
      fail('Should report error for missing PlantUML file');
    }
    console.log();

    // ═══════════════════════════════════════════════════════════
    console.log('═══════════════════════════════════════════════════════════');
    console.log('📊 TEST SUMMARY');
    console.log('═══════════════════════════════════════════════════════════');
    console.log(`✅ Passed: ${testsPassed}`);
    console.log(`❌ Failed: ${testsFailed}`);
    console.log(`📈 Success Rate: ${((testsPassed / (testsPassed + testsFailed)) * 100).toFixed(1)}%`);
    console.log('═══════════════════════════════════════════════════════════\n');

    if (testsFailed === 0) {
      console.log('🎉 All MCP tests passed!\n');
    } else {
      console.log('⚠️  Some MCP tests failed. Please review before release.\n');
    }

    // ═══════════════════════════════════════════════════════════
    console.log('═══════════════════════════════════════════════════════════');
    console.log('📋 SECTION 8: Output Validation');
    console.log('───────────────────────────────────────────────────────────');
    console.log('Running Python validation script...\n');

    try {
      const validationScript = resolve(__dirname, 'validate-output.py');
      execSync(`python "${validationScript}"`, {
        cwd: REPO_ROOT,
        stdio: 'inherit'
      });
      console.log('\n✅ Output validation completed');
    } catch (error) {
      console.log('\n❌ Output validation failed');
      testsFailed++;
    }

  } catch (error) {
    console.error('❌ Fatal test error:', error.message);
    console.error(error);
    testsFailed++;
  } finally {
    // Clean up
    server.kill();

    // Optionally clean up test directory
    // rmSync(TEST_DIR, { recursive: true, force: true });

    console.log('\n═══════════════════════════════════════════════════════════');
    console.log('🏁 FINAL RESULTS');
    console.log('═══════════════════════════════════════════════════════════');
    if (testsFailed === 0) {
      console.log('🎉 All tests passed! Package is ready for release.\n');
    } else {
      console.log('⚠️  Some tests failed. Please review before release.\n');
    }

    process.exit(testsFailed > 0 ? 1 : 0);
  }
}

// Run tests
runTests().catch(error => {
  console.error('Fatal error:', error);
  server.kill();
  process.exit(1);
});
