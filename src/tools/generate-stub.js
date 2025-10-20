/**
 * Document Stub Generator Tool Handler
 *
 * MCP tool for generating new markdown document stubs from the template
 * with customizable YAML front matter
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import {
  resolvePath,
  createSuccessResponse,
  createErrorResponse
} from '../utils.js';

// Get the package root directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PACKAGE_ROOT = resolve(__dirname, '..', '..');
const TEMPLATE_PATH = resolve(PACKAGE_ROOT, 'docs', 'TEMPLATE_Document.md');

/**
 * Tool definition for MCP server
 */
export const toolDefinition = {
  name: 'dilon_generate_stub',
  description: 'Generates a new Dilon document stub from the template with customizable YAML front matter. ' +
               'Creates a markdown file ready for content authoring following Dilon documentation standards. ' +
               'Reference the dilon://styling/markdown resource for detailed markdown styling guidelines before writing document content.',
  inputSchema: {
    type: 'object',
    properties: {
      output_path: {
        type: 'string',
        description: 'Path where the new markdown stub file will be created'
      },
      title: {
        type: 'string',
        description: 'Document title (appears in header and metadata)'
      },
      author: {
        type: 'string',
        description: 'Primary author name or team name'
      },
      department: {
        type: 'string',
        description: 'Department name (default: "--")'
      },
      doc_number: {
        type: 'string',
        description: 'Dilon document number (e.g., DD_XXX_XXXXX). Must be specified by user.'
      },
      current_revision: {
        type: 'string',
        description: 'Current revision number (default: "00")'
      },
      regulatory_rep: {
        type: 'string',
        description: 'Regulatory representative name (default: "--")'
      },
      quality_rep: {
        type: 'string',
        description: 'Quality representative name (default: "--")'
      },
      department_head: {
        type: 'string',
        description: 'Department head name (default: "--")'
      },
      revision_description: {
        type: 'string',
        description: 'Description for the initial revision entry (default: "Initial release")'
      },
      eco_number: {
        type: 'string',
        description: 'ECO number for the initial revision (default: "ECO-TBD")'
      },
      eco_date: {
        type: 'string',
        description: 'ECO date for the initial revision in YYYY-MM-DD format (default: "YYYY-MM-DD")'
      }
    },
    required: ['output_path']
  }
};

/**
 * Execute the document stub generator
 *
 * @param {Object} args - Tool arguments from MCP
 * @param {Object} config - Configuration from loadConfig() (unused but provided for consistency)
 * @returns {Promise<Object>} MCP response
 */
export async function execute(args, config) {
  try {
    // Validate template exists
    if (!existsSync(TEMPLATE_PATH)) {
      return createErrorResponse(
        '❌ Template not found',
        `Template file does not exist at: ${TEMPLATE_PATH}`
      );
    }

    // Read the template
    let templateContent;
    try {
      templateContent = readFileSync(TEMPLATE_PATH, 'utf-8');
    } catch (error) {
      return createErrorResponse(
        '❌ Failed to read template',
        `Could not read template file: ${error.message}`
      );
    }

    // Resolve output path
    const outputPath = resolvePath(args.output_path);

    // Check if output file already exists
    if (existsSync(outputPath)) {
      return createErrorResponse(
        '❌ File already exists',
        `Output file already exists: ${outputPath}\nPlease choose a different path or delete the existing file.`
      );
    }

    // Extract YAML front matter defaults from template
    const yamlMatch = templateContent.match(/^---[\r\n]+([\s\S]*?)[\r\n]+---/m);
    if (!yamlMatch) {
      return createErrorResponse(
        '❌ Invalid template',
        `Template does not contain valid YAML front matter\nTemplate path: ${TEMPLATE_PATH}\nTemplate start: ${templateContent.substring(0, 100)}`
      );
    }

    // Build replacement map with user values or defaults
    const replacements = {
      title: args.title || 'Document Title',
      author: args.author || 'Author Name',
      department: args.department || '--',
      doc_number: args.doc_number || 'DD_XXX_XXXXX',
      current_revision: args.current_revision || '00',
      regulatory_rep: args.regulatory_rep || '--',
      quality_rep: args.quality_rep || '--',
      department_head: args.department_head || '--',
      revision_number: args.current_revision || '00',
      revision_description: args.revision_description || 'Initial release',
      eco_number: args.eco_number || 'ECO-TBD',
      eco_date: args.eco_date || 'YYYY-MM-DD'
    };

    // Apply replacements to template
    let outputContent = templateContent;
    outputContent = outputContent.replace(/title: ".*?"/, `title: "${replacements.title}"`);
    outputContent = outputContent.replace(/author: ".*?"/, `author: "${replacements.author}"`);
    outputContent = outputContent.replace(/department: ".*?"/, `department: "${replacements.department}"`);
    outputContent = outputContent.replace(/doc_number: ".*?"/, `doc_number: "${replacements.doc_number}"`);
    outputContent = outputContent.replace(/current_revision: ".*?"/, `current_revision: "${replacements.current_revision}"`);
    outputContent = outputContent.replace(/regulatory_rep: ".*?"/, `regulatory_rep: "${replacements.regulatory_rep}"`);
    outputContent = outputContent.replace(/quality_rep: ".*?"/, `quality_rep: "${replacements.quality_rep}"`);
    outputContent = outputContent.replace(/department_head: ".*?"/, `department_head: "${replacements.department_head}"`);

    // Update revision entry (match the revision number to current_revision)
    outputContent = outputContent.replace(
      /- number: ".*?"\s+description: ".*?"\s+eco_number: ".*?"\s+eco_date: ".*?"/,
      `- number: "${replacements.revision_number}"
    description: "${replacements.revision_description}"
    eco_number: "${replacements.eco_number}"
    eco_date: "${replacements.eco_date}"`
    );

    // Write the output file
    try {
      writeFileSync(outputPath, outputContent, 'utf-8');
    } catch (error) {
      return createErrorResponse(
        '❌ Failed to write file',
        `Could not write output file: ${error.message}`
      );
    }

    // Build success message
    const successMessage = [
      '✅ Document stub created successfully',
      '',
      `📄 Output: ${outputPath}`,
      '',
      '📋 Document metadata:',
      `  • Title: ${replacements.title}`,
      `  • Author: ${replacements.author}`,
      `  • Department: ${replacements.department}`,
      `  • Doc Number: ${replacements.doc_number}`,
      `  • Revision: ${replacements.current_revision}`,
      '',
      '📝 Next steps:',
      '  1. Edit the document content in the markdown file',
      '  2. Reference the dilon://styling/markdown resource for styling guidelines',
      '  3. Use dilon_compile_doc to generate the final Word document'
    ].join('\n');

    return createSuccessResponse(
      '✅ Document stub created',
      successMessage
    );

  } catch (error) {
    return createErrorResponse(
      '❌ Unexpected error',
      `Failed to generate document stub: ${error.message}\n\nStack trace:\n${error.stack}`
    );
  }
}
