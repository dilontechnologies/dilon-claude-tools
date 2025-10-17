/**
 * Utility Functions for Dilon Claude Tools MCP Server
 *
 * Provides helper functions for executing commands and handling responses
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { resolve, isAbsolute } from 'path';

const execAsync = promisify(exec);

/**
 * Execute a command asynchronously and return the result
 *
 * @param {string} command - Command to execute
 * @param {Object} options - Execution options (cwd, env, etc.)
 * @returns {Promise<Object>} Object with stdout, stderr, and success status
 */
export async function executeCommand(command, options = {}) {
  try {
    const { stdout, stderr } = await execAsync(command, {
      maxBuffer: 10 * 1024 * 1024, // 10 MB buffer for large outputs
      ...options
    });

    return {
      success: true,
      stdout: stdout.trim(),
      stderr: stderr.trim(),
      error: null
    };
  } catch (error) {
    return {
      success: false,
      stdout: error.stdout ? error.stdout.trim() : '',
      stderr: error.stderr ? error.stderr.trim() : '',
      error: error.message
    };
  }
}

/**
 * Execute a PowerShell command on Windows
 *
 * @param {string} psCommand - PowerShell command to execute
 * @param {Object} options - Execution options
 * @returns {Promise<Object>} Execution result
 */
export async function executePowerShell(psCommand, options = {}) {
  const command = `powershell -Command "${psCommand.replace(/"/g, '\\"')}"`;
  return executeCommand(command, options);
}

/**
 * Execute a Python script with arguments
 *
 * @param {string} pythonPath - Path to Python executable
 * @param {string} scriptPath - Path to Python script
 * @param {Array<string>} args - Script arguments
 * @param {Object} options - Execution options
 * @returns {Promise<Object>} Execution result
 */
export async function executePython(pythonPath, scriptPath, args = [], options = {}) {
  const quotedArgs = args.map(arg => `"${arg}"`).join(' ');
  const command = `${pythonPath} "${scriptPath}" ${quotedArgs}`;
  return executeCommand(command, options);
}

/**
 * Resolve a file path (absolute or relative to cwd)
 *
 * @param {string} filePath - File path to resolve
 * @param {string} basePath - Base path for relative paths (defaults to cwd)
 * @returns {string} Absolute path
 */
export function resolvePath(filePath, basePath = process.cwd()) {
  if (isAbsolute(filePath)) {
    return resolve(filePath);
  }
  return resolve(basePath, filePath);
}

/**
 * Format an MCP tool success response
 *
 * @param {string} message - Success message
 * @param {Object} data - Additional data to include
 * @returns {Object} MCP response object
 */
export function createSuccessResponse(message, data = {}) {
  return {
    content: [
      {
        type: 'text',
        text: message
      }
    ],
    ...data
  };
}

/**
 * Format an MCP tool error response
 *
 * @param {string} message - Error message
 * @param {string} details - Detailed error information
 * @returns {Object} MCP error response object
 */
export function createErrorResponse(message, details = '') {
  const errorText = details ? `${message}\n\nDetails:\n${details}` : message;

  return {
    content: [
      {
        type: 'text',
        text: errorText
      }
    ],
    isError: true
  };
}

/**
 * Validate that a file path exists and is accessible
 *
 * @param {string} filePath - File path to validate
 * @param {string} fileDescription - Description of the file for error messages
 * @returns {Object} Validation result with error message if invalid
 */
export function validateFilePath(filePath, fileDescription = 'File') {
  const { existsSync } = await import('fs');

  if (!filePath) {
    return {
      valid: false,
      error: `${fileDescription} path is required`
    };
  }

  if (!existsSync(filePath)) {
    return {
      valid: false,
      error: `${fileDescription} not found at: ${filePath}`
    };
  }

  return { valid: true };
}

/**
 * Generate default output path by changing file extension
 *
 * @param {string} inputPath - Input file path
 * @param {string} newExtension - New file extension (e.g., '.docx')
 * @returns {string} Output path with new extension
 */
export function generateOutputPath(inputPath, newExtension) {
  const { parse, format } = await import('path');
  const parsed = parse(inputPath);

  return format({
    dir: parsed.dir,
    name: parsed.name,
    ext: newExtension
  });
}
