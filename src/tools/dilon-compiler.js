/**
 * Dilon Document Compiler Tool Handler
 *
 * MCP tool for compiling Markdown files with YAML front matter
 * into formatted Dilon Word documents
 */

import { existsSync } from 'fs';
import { parse, format } from 'path';
import { getDilonCompilerPaths } from '../config.js';
import {
  executePython,
  resolvePath,
  createSuccessResponse,
  createErrorResponse
} from '../utils.js';

/**
 * Tool definition for MCP server
 */
export const toolDefinition = {
  name: 'dilon_compile_doc',
  description: 'Compiles a Markdown file with YAML front matter into a formatted Dilon Word document. ' +
               'Uses the Dilon Document Compiler to generate regulatory-compliant Word documents with ' +
               'signature pages, revision tables, and table of contents. ' +
               'IMPORTANT: Reference the dilon://styling/markdown resource for detailed markdown styling guidelines before compiling documents.',
  inputSchema: {
    type: 'object',
    properties: {
      input_markdown: {
        type: 'string',
        description: 'Path to the input Markdown file (.md) with YAML front matter'
      },
      output_word: {
        type: 'string',
        description: 'Path to the output Word file (.docx). If not specified, uses same name as input with .docx extension'
      },
      signature_template: {
        type: 'string',
        description: 'Path to custom signature template (Part A). If not specified, uses default template'
      },
      content_template: {
        type: 'string',
        description: 'Path to custom content template (Part C). If not specified, uses default template'
      }
    },
    required: ['input_markdown']
  }
};

/**
 * Execute the Dilon Document Compiler
 *
 * @param {Object} args - Tool arguments from MCP
 * @param {Object} config - Configuration from loadConfig()
 * @returns {Promise<Object>} MCP response
 */
export async function execute(args, config) {
  try {
    // Resolve input path
    const inputPath = resolvePath(args.input_markdown);

    // Validate input file exists
    if (!existsSync(inputPath)) {
      return createErrorResponse(
        '❌ Input file not found',
        `The specified Markdown file does not exist: ${inputPath}`
      );
    }

    // Validate input file is .md
    const inputExt = parse(inputPath).ext.toLowerCase();
    if (inputExt !== '.md') {
      return createErrorResponse(
        '❌ Invalid input file',
        `Input file must be a Markdown (.md) file. Got: ${inputExt}`
      );
    }

    // Generate output path if not specified
    let outputPath;
    if (args.output_word) {
      outputPath = resolvePath(args.output_word);
    } else {
      const parsed = parse(inputPath);
      outputPath = format({
        dir: parsed.dir,
        name: parsed.name,
        ext: '.docx'
      });
    }

    // Get compiler paths (embedded in this repo)
    const compilerPaths = getDilonCompilerPaths();

    // Validate compiler script exists
    if (!existsSync(compilerPaths.scriptPath)) {
      return createErrorResponse(
        '❌ Dilon Compiler not found',
        `The compiler script is not at the expected location: ${compilerPaths.scriptPath}\n\n` +
        `This is an installation error. Please re-clone the repository or run npm install.`
      );
    }

    // Build Python command arguments
    const pythonArgs = [inputPath, outputPath];

    // Add custom templates if specified
    if (args.signature_template) {
      const sigTemplatePath = resolvePath(args.signature_template);
      if (!existsSync(sigTemplatePath)) {
        return createErrorResponse(
          '❌ Signature template not found',
          `Custom signature template does not exist: ${sigTemplatePath}`
        );
      }
      pythonArgs.push(sigTemplatePath);

      // If signature template is specified, content template must also be specified
      if (args.content_template) {
        const contentTemplatePath = resolvePath(args.content_template);
        if (!existsSync(contentTemplatePath)) {
          return createErrorResponse(
            '❌ Content template not found',
            `Custom content template does not exist: ${contentTemplatePath}`
          );
        }
        pythonArgs.push(contentTemplatePath);
      } else {
        // Use default content template
        pythonArgs.push(compilerPaths.contentTemplate);
      }
    } else if (args.content_template) {
      // Content template without signature template - use default signature
      pythonArgs.push(compilerPaths.signatureTemplate);

      const contentTemplatePath = resolvePath(args.content_template);
      if (!existsSync(contentTemplatePath)) {
        return createErrorResponse(
          '❌ Content template not found',
          `Custom content template does not exist: ${contentTemplatePath}`
        );
      }
      pythonArgs.push(contentTemplatePath);
    }

    // Execute the Python compiler script
    const result = await executePython(
      config.pythonPath,
      compilerPaths.scriptPath,
      pythonArgs
    );

    // Check for execution errors
    if (!result.success) {
      return createErrorResponse(
        '❌ Document compilation failed',
        `${result.error}\n\nStderr:\n${result.stderr}\n\nStdout:\n${result.stdout}`
      );
    }

    // Check if output file was created
    if (!existsSync(outputPath)) {
      return createErrorResponse(
        '❌ Output file not created',
        `The compiler executed but did not create the output file at: ${outputPath}\n\n` +
        `Stdout:\n${result.stdout}\n\nStderr:\n${result.stderr}`
      );
    }

    // Success!
    return createSuccessResponse(
      `✅ Document compiled successfully!\n\n` +
      `📄 Input:  ${inputPath}\n` +
      `📦 Output: ${outputPath}\n\n` +
      `${result.stdout}`
    );

  } catch (error) {
    return createErrorResponse(
      '❌ Unexpected error during compilation',
      error.message
    );
  }
}
