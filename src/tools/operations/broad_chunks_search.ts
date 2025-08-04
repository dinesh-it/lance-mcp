import { chunksVectorStore } from "../../lancedb/client.js";
import { BaseTool, ToolParams } from "../base/tool.js";
import * as path from 'path';

export interface BroadSearchParams extends ToolParams {
  text: string;
}

export class BroadSearchTool extends BaseTool<BroadSearchParams> {
  name = "all_chunks_search";
  description = "Search for relevant document chunks in the vector store across all documents. Use with caution as it can return information from irrelevant sources";
  inputSchema = {
    type: "object" as const,
    properties: {
      text: {
        type: "string",
        description: "Search string",
        default: {},
      }
    },
    required: ["text"],
  };

  async execute(params: BroadSearchParams) {
    try {
      const retriever = chunksVectorStore.asRetriever();
      const results = await retriever.invoke(params.text);

      // Format results with file and page references
      const formattedResults = this.formatResultsWithReferences(results);

      return {
        content: [
          { type: "text" as const, text: formattedResults },
        ],
        isError: false,
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  private formatResultsWithReferences(results: any[]): string {
    if (!results || results.length === 0) {
      return "No results found.";
    }

    let formattedOutput = "Search Results:\n\n";
    
    results.forEach((result, index) => {
      const fileName = result.metadata?.source ? 
        result.metadata.source.split('/').pop() : 'Unknown file';
      const pageInfo = this.extractPageInfo(result.metadata?.loc);
      
      formattedOutput += `**Result ${index + 1}**\n`;
      formattedOutput += `📄 **Source**: ${fileName}`;
      if (pageInfo) {
        formattedOutput += ` (Page ${pageInfo})`;
      }
      formattedOutput += "\n";
      if (result.metadata?.source) {
        formattedOutput += `🔗 **File Path**: ${result.metadata.source}\n`;
      }
      formattedOutput += `📝 **Content**: ${result.pageContent}\n`;
      formattedOutput += "---\n\n";
    });
    
    return formattedOutput;
  }

  private extractPageInfo(loc: any): string | null {
    if (!loc) return null;
    
    // Handle different loc formats
    if (typeof loc === 'object') {
      // Check for common page number fields
      if (loc.pageNumber !== undefined) {
        return loc.pageNumber.toString();
      }
      if (loc.page !== undefined) {
        return loc.page.toString();
      }
      // For PDF loader loc format
      if (loc.lines && loc.lines.from !== undefined) {
        return `Line ${loc.lines.from}${loc.lines.to ? `-${loc.lines.to}` : ''}`;
      }
    }
    
    // If loc is a string or number, try to extract page info
    if (typeof loc === 'string' || typeof loc === 'number') {
      return loc.toString();
    }
    
    return null;
  }
}
