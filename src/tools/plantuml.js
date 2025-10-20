/**
 * PlantUML Diagram Generator Tool Handler
 *
 * MCP tool for generating diagrams from PlantUML files
 * using Dilon styling conventions
 */

import { existsSync } from 'fs';
import { parse, format, join } from 'path';
import { getPlantUMLStyleGuide } from '../config.js';
import {
  executePowerShell,
  resolvePath,
  createSuccessResponse,
  createErrorResponse
} from '../utils.js';

/**
 * Tool definition for MCP server
 */
export const toolDefinition = {
  name: 'dilon_plantuml',
  description: 'Generates diagrams from PlantUML (.puml) files using Dilon styling conventions. ' +
               'Supports PNG, SVG, and PDF output formats. ' +
               'IMPORTANT: Reference the dilon://styling/plantuml resource for detailed PlantUML styling guidelines before generating diagrams.',
  inputSchema: {
    type: 'object',
    properties: {
      input_file: {
        type: 'string',
        description: 'Path to the PlantUML (.puml) file to convert'
      },
      output_format: {
        type: 'string',
        enum: ['png', 'svg', 'pdf'],
        description: 'Output format for the diagram (default: png)'
      },
      output_path: {
        type: 'string',
        description: 'Custom output path for the generated diagram. If not specified, uses input filename with appropriate extension in same directory'
      }
    },
    required: ['input_file']
  }
};

/**
 * Execute PlantUML diagram generation
 *
 * @param {Object} args - Tool arguments from MCP
 * @param {Object} config - Configuration from loadConfig()
 * @returns {Promise<Object>} MCP response
 */
export async function execute(args, config) {
  try {
    // Resolve input path
    const inputPath = resolvePath(args.input_file);

    // Validate input file exists
    if (!existsSync(inputPath)) {
      return createErrorResponse(
        '❌ Input file not found',
        `The specified PlantUML file does not exist: ${inputPath}`
      );
    }

    // Validate input file is .puml
    const inputExt = parse(inputPath).ext.toLowerCase();
    if (inputExt !== '.puml') {
      return createErrorResponse(
        '❌ Invalid input file',
        `Input file must be a PlantUML (.puml) file. Got: ${inputExt}`
      );
    }

    // Determine output format (default to PNG)
    const outputFormat = (args.output_format || 'png').toLowerCase();
    const formatFlag = `-t${outputFormat}`;

    // Generate output path if not specified
    let outputPath;
    if (args.output_path) {
      outputPath = resolvePath(args.output_path);
    } else {
      const parsed = parse(inputPath);
      outputPath = format({
        dir: parsed.dir,
        name: parsed.name,
        ext: `.${outputFormat}`
      });
    }

    // Validate PlantUML installation
    const plantUmlJar = join(config.plantUmlPath, 'plantuml.jar');
    if (!existsSync(plantUmlJar)) {
      return createErrorResponse(
        '❌ PlantUML not found',
        `PlantUML jar file not found at: ${plantUmlJar}\n\n` +
        `Please verify your PlantUML installation path in .dilon-tools-config.json`
      );
    }

    // Build PlantUML command
    // Use PowerShell alias 'plantuml' if available, otherwise use java -jar
    const plantUmlCommand = `plantuml ${formatFlag} "${inputPath}"`;

    // Execute PlantUML
    const result = await executePowerShell(plantUmlCommand);

    // Check for execution errors
    if (!result.success) {
      // Try fallback to java -jar if plantuml alias not found
      if (result.error && result.error.includes('not recognized')) {
        const javaCommand = `java -jar "${plantUmlJar}" ${formatFlag} "${inputPath}"`;
        const javaResult = await executePowerShell(javaCommand);

        if (!javaResult.success) {
          return createErrorResponse(
            '❌ PlantUML execution failed',
            `Both 'plantuml' command and 'java -jar' execution failed.\n\n` +
            `Error: ${javaResult.error}\n\nStderr:\n${javaResult.stderr}\n\nStdout:\n${javaResult.stdout}\n\n` +
            `Please ensure PlantUML is properly installed and Java is available in PATH.`
          );
        }

        // Java execution succeeded, continue with validation
        result.stdout = javaResult.stdout;
        result.stderr = javaResult.stderr;
      } else {
        return createErrorResponse(
          '❌ PlantUML execution failed',
          `${result.error}\n\nStderr:\n${result.stderr}\n\nStdout:\n${result.stdout}`
        );
      }
    }

    // Check if output file was created
    if (!existsSync(outputPath)) {
      return createErrorResponse(
        '❌ Output file not created',
        `PlantUML executed but did not create the output file at: ${outputPath}\n\n` +
        `Stdout:\n${result.stdout}\n\nStderr:\n${result.stderr}\n\n` +
        `Note: PlantUML may have generated the file with a different name. Check the input directory.`
      );
    }

    // Get style guide reference (embedded in this repo)
    const styleGuidePath = getPlantUMLStyleGuide();
    const styleGuideNote = existsSync(styleGuidePath)
      ? `\n\n📘 Styling Guide: ${styleGuidePath}`
      : '';

    // Success!
    return createSuccessResponse(
      `✅ Diagram generated successfully!\n\n` +
      `📄 Input:  ${inputPath}\n` +
      `📦 Output: ${outputPath}\n` +
      `🎨 Format: ${outputFormat.toUpperCase()}` +
      styleGuideNote
    );

  } catch (error) {
    return createErrorResponse(
      '❌ Unexpected error during diagram generation',
      error.message
    );
  }
}
